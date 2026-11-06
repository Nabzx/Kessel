"""CPU synthetic loader kernel. This is not a calibrated vehicle simulator."""

from dataclasses import asdict, dataclass
import hashlib
import math

import numpy as np

from .contracts import LoaderConfig, canonical_json, validate_actions
from .dynamics import clearance, release_material, traction
from .kinematics import advance, components
from .pile import PileGrid
from .rewards import RewardConfig, calculate

PROPRIO_NAMES = (
    "odometry_x_m", "odometry_y_m", "heading_sin", "heading_cos",
    "speed_m_s", "articulation_rad", "boom_rad", "bucket_rad", "load_kg",
    "receiver_forward_m", "receiver_left_m", "range_age_s", "range_fresh",
    "elapsed_s", "slip_ratio",
)


@dataclass(frozen=True)
class SceneConfig:
    max_steps: int = 600
    success_kg: float = 2000.0
    stuck_s: float = 10.0
    half_width_m: float = 4.2
    ceiling_m: float = 3.2
    friction: float = 0.6
    grade_rad: float = 0.0
    pile_resistance_n_m: float = 18000.0
    sensor_noise: float = 0.0
    dropout: float = 0.0
    occlusion: float = 0.0
    randomise: bool = False
    obstacles: tuple = ()

    def __post_init__(self):
        if isinstance(self.max_steps, bool) or not isinstance(self.max_steps, int) or self.max_steps < 1:
            raise ValueError("max_steps must be a positive integer")
        positive = ("success_kg", "stuck_s", "half_width_m", "ceiling_m", "friction")
        nonnegative = ("pile_resistance_n_m", "sensor_noise")
        for name in positive + nonnegative + ("grade_rad", "dropout", "occlusion"):
            value = getattr(self, name)
            if not math.isfinite(value):
                raise ValueError(f"{name} must be finite")
            if name in positive and value <= 0 or name in nonnegative and value < 0:
                raise ValueError(f"invalid {name}")
        if not 0 <= self.dropout <= 1 or not 0 <= self.occlusion <= 1:
            raise ValueError("dropout and occlusion must be probabilities")
        if abs(self.grade_rad) > 0.3 or self.half_width_m < 1 or self.ceiling_m < 1.9:
            raise ValueError("scene exceeds the supported grade or clearance range")
        for box in self.obstacles:
            if len(box) != 4 or not np.isfinite(box).all() or box[0] >= box[1] or box[2] >= box[3]:
                raise ValueError("obstacles must be finite increasing xy bounds")

    def digest(self):
        return hashlib.sha256(canonical_json(asdict(self)).encode()).hexdigest()


class LoaderEnv:
    """Independent batch slots with explicit masked reset and no autoreset.

    step -> observation dict, reward (N,), terminated (N,), truncated (N,), info.
    Observation: proprio (N,15), local_height_m (N,5,5), range_valid (N,5,5).
    Only diagnostics expose full synthetic state. All returned arrays are copies.
    """

    metadata = {"autoreset_mode": "disabled", "source_mode": "recorded_synthetic"}

    def __init__(self, num_envs=1, *, seed=0, loader=None, scene=None, stream_ids=None, reward=None):
        if isinstance(num_envs, bool) or not isinstance(num_envs, int) or num_envs <= 0:
            raise ValueError("num_envs must be a positive integer")
        self.num_envs = num_envs
        self.loader = loader or LoaderConfig()
        self.scene = scene or SceneConfig()
        self.reward_config = reward or RewardConfig(mass_scale_kg=self.loader.payload_kg)
        if (self.loader.length_m, self.loader.width_m, self.loader.height_m) != (7.1, 1.5, 1.9):
            raise ValueError("reference geometry supports the documented 7.1 x 1.5 x 1.9 m envelope")
        if (self.loader.forward_m_s > 2 or self.loader.reverse_m_s > 1.5
                or self.loader.articulation_rate_rad_s > 0.35):
            raise ValueError("reference clearance supports speeds <=2/1.5 m/s and articulation <=0.35 rad/s")
        if self.scene.success_kg > self.loader.payload_kg:
            raise ValueError("one-cycle success mass cannot exceed bucket capacity")
        ids = np.arange(num_envs) if stream_ids is None else np.asarray(stream_ids)
        if ids.shape != (num_envs,) or ids.dtype.kind not in "iu" or (ids < 0).any() or len(set(ids)) != num_envs:
            raise ValueError("stream_ids must be distinct non-negative integers")
        self.stream_ids = ids.astype(np.int64)
        self.seeds = np.zeros(num_envs, dtype=np.int64)
        self.episode_index = np.full(num_envs, -1, dtype=np.int64)
        self.sensor_rng = [None] * num_envs
        self.pose = np.zeros((num_envs, 3))
        self.joints = np.zeros((num_envs, 3))
        self.speed = np.zeros(num_envs)
        self.wheel_angles = np.zeros((num_envs, 4))
        self.payload = np.zeros(num_envs)
        self.delivered = np.zeros(num_envs)
        self.spilled = np.zeros(num_envs)
        self.effort = np.zeros(num_envs)
        self.slip_s = np.zeros(num_envs)
        self.last_slip = np.zeros(num_envs)
        self.stuck_time = np.zeros(num_envs)
        self.elapsed = np.zeros(num_envs)
        self.steps = np.zeros(num_envs, dtype=np.int64)
        self.peak_load = np.zeros(num_envs)
        self.terminated = np.zeros(num_envs, dtype=bool)
        self.truncated = np.zeros(num_envs, dtype=bool)
        self.reason = np.full(num_envs, "", dtype="U48")
        self.collision_time = np.full(num_envs, -1.0)
        self.impact_speed = np.zeros(num_envs)
        self.half_width = np.full(num_envs, self.scene.half_width_m, dtype=float)
        self.friction = np.full(num_envs, self.scene.friction, dtype=float)
        self.grade = np.full(num_envs, self.scene.grade_rad, dtype=float)
        self.resistance = np.full(num_envs, self.scene.pile_resistance_n_m, dtype=float)
        self.receiver = np.tile([-1.5, 0.0], (num_envs, 1))
        self.receiver_half = np.array([1.6, 2.0])
        self.pile = PileGrid(num_envs)
        self.initial_pile_hashes = [""]*num_envs
        self.initial_pose = np.zeros((num_envs, 3))
        self._crop = np.zeros((num_envs, 5, 5))
        self._valid = np.zeros((num_envs, 5, 5))
        self._age = np.zeros(num_envs)
        self._fresh = np.zeros(num_envs)
        self._proprio = np.zeros((num_envs, len(PROPRIO_NAMES)))
        self.reset(seed=seed)

    def reset(self, *, seed=None, mask=None):
        selected = np.ones(self.num_envs, dtype=bool) if mask is None else np.asarray(mask)
        if selected.shape != (self.num_envs,) or selected.dtype != bool:
            raise ValueError("reset mask must be a boolean batch vector")
        if seed is not None:
            if isinstance(seed, bool) or not isinstance(seed, int) or not 0 <= seed < 2**63:
                raise ValueError("seed must be a non-negative 63-bit integer")
            self.seeds[selected] = seed
            self.episode_index[selected] = -1
        for i in np.flatnonzero(selected):
            self.episode_index[i] += 1
            scenario_seed, sensor_seed = np.random.SeedSequence(
                [int(self.seeds[i]), int(self.stream_ids[i]), int(self.episode_index[i])]
            ).spawn(2)
            rng = np.random.default_rng(scenario_seed)
            self.sensor_rng[i] = np.random.default_rng(sensor_seed)
            self.pose[i] = (0, rng.uniform(-0.1, 0.1), 0)
            self.joints[i] = (0, 0, -0.1)
            self.pile.reset_one(i, rng, pile_front=rng.uniform(7.5, 8.5))
            self.initial_pile_hashes[i] = hashlib.sha256(
                self.pile.height[i].astype("<f8").tobytes()).hexdigest()
            self.initial_pose[i] = self.pose[i]
            self.half_width[i] = self.scene.half_width_m
            self.friction[i] = self.scene.friction
            self.grade[i] = self.scene.grade_rad
            self.resistance[i] = self.scene.pile_resistance_n_m
            if self.scene.randomise:
                self.pile.origin[i, 1] += rng.uniform(-0.25, 0.25)
                self.half_width[i] *= rng.uniform(0.9, 1.1)
                self.friction[i] *= rng.uniform(0.7, 1.2)
                self.grade[i] += rng.uniform(-0.06, 0.06)
                self.resistance[i] *= rng.uniform(0.7, 1.3)
            for array in (self.speed, self.wheel_angles, self.payload, self.delivered,
                          self.spilled, self.effort, self.slip_s, self.last_slip,
                          self.stuck_time, self.elapsed, self.steps, self.peak_load,
                          self.terminated, self.truncated, self.impact_speed,
                          self._crop, self._valid, self._age, self._fresh):
                array[i] = 0
            self.reason[i] = ""
            self.collision_time[i] = -1
        self._update_observations(selected, reset=True)
        return self.observe(), self.diagnostics()

    def observe(self):
        return {"proprio": self._proprio.copy(), "local_height_m": self._crop.copy(),
                "range_valid": self._valid.copy()}

    def _update_observations(self, selected, reset=False):
        indices = np.flatnonzero(selected)
        if not len(indices):
            return
        geometry = components(self.pose, self.joints)
        lateral = np.stack((-geometry["front_forward"][:, 1], geometry["front_forward"][:, 0]), axis=1)
        along, across = np.meshgrid(np.arange(-1, 4)*0.75, np.arange(-2, 3)*0.75, indexing="ij")
        points = (geometry["mouth"][:, None, None, :]
                  + along[None, ..., None]*geometry["front_forward"][:, None, None, :]
                  + across[None, ..., None]*lateral[:, None, None, :])
        height = self.pile.sample(points)[indices]
        # Only independent RNG streams need a slot loop. Sensor arithmetic is
        # vectorised, with the same draw order as the scalar reference.
        normals = np.stack([self.sensor_rng[i].normal(size=40) for i in indices])
        uniforms = np.stack([self.sensor_rng[i].random(size=26) for i in indices])
        noise, range_noise = normals[:, :15], normals[:, 15:].reshape(-1, 5, 5)
        fresh = uniforms[:, 0] >= self.scene.dropout
        visible = uniforms[:, 1:].reshape(-1, 5, 5) >= self.scene.occlusion
        scale = self.scene.sensor_noise
        crop = np.where(visible, np.maximum(0, height + range_noise*0.01*scale), 0)
        self._crop[indices] = np.where(fresh[:, None, None], crop, self._crop[indices])
        self._valid[indices] = visible & fresh[:, None, None]
        self._age[indices] = np.where(fresh, 0, self._age[indices] + (0 if reset else self.loader.decision_s))
        self._fresh[indices] = fresh
        odometry = self.pose[indices, :2] + noise[:, :2]*0.01*scale
        heading = self.pose[indices, 2] + noise[:, 2]*0.005*scale
        forward = np.stack((np.cos(heading), np.sin(heading)), axis=1)
        left = np.stack((-forward[:, 1], forward[:, 0]), axis=1)
        receiver = self.receiver[indices] - odometry
        self._proprio[indices] = np.column_stack((
            odometry, np.sin(heading), np.cos(heading),
            self.speed[indices] + noise[:, 3]*0.005*scale,
            self.joints[indices] + noise[:, 4:7]*0.002*scale,
            np.clip(self.payload[indices] + noise[:, 7]*20*scale, 0, self.loader.payload_kg),
            np.sum(receiver*forward, axis=1), np.sum(receiver*left, axis=1),
            self._age[indices], fresh, self.elapsed[indices], self.last_slip[indices],
        ))

    def step(self, actions):
        actions = validate_actions(actions, self.num_envs)
        if (self.terminated | self.truncated).any():
            raise RuntimeError("reset finished slots explicitly before stepping")
        # Keep physical increments at <=20 ms even for large decision intervals.
        substeps = max(self.loader.substeps, math.ceil(self.loader.decision_s / 0.02))
        dt = self.loader.decision_s / substeps
        before_delivered, before_spilled = self.delivered.copy(), self.spilled.copy()
        before_effort, before_slip = self.effort.copy(), self.slip_s.copy()
        before_elapsed = self.elapsed.copy()
        removed_cells = np.zeros_like(self.pile.height)
        loaded = np.zeros(self.num_envs)
        last_mouth = components(self.pose, self.joints)["mouth"].copy()
        for _ in range(substeps):
            active = ~self.terminated
            controls = actions * active[:, None]
            old_pose, old_joints = self.pose.copy(), self.joints.copy()
            old_wheels, old_speed = self.wheel_angles.copy(), self.speed.copy()
            acceleration, slip, drive, _ = traction(
                self.pose, self.speed, self.joints, self.payload, controls[:, 0],
                self.pile, self.friction, self.grade, self.resistance,
                self.loader.acceleration_m_s2, dt,
            )
            geometry = advance(self.pose, self.speed, self.joints, self.wheel_angles,
                               controls, acceleration*active, self.loader, dt)
            # Prevent resistance alone from reversing a coasting machine.
            crossed = (old_speed*self.speed < 0) & (controls[:, 0] == 0)
            self.speed[crossed] = 0
            collision = clearance(old_pose, old_joints, self.pose, self.joints,
                                  self.half_width, self.scene.ceiling_m, self.scene.obstacles)
            hit = active & (collision != "")
            self.reason[hit] = collision[hit]
            self.collision_time[hit] = self.elapsed[hit] + dt
            self.impact_speed[hit] = np.abs(self.speed[hit])
            self.terminated[hit] = True
            # A blocked chassis cannot travel through the uncollected pile.
            front_height = self.pile.sample(geometry["front"])
            blocked = active & ~hit & (self.speed > 0) & (front_height > 0.5)
            rollback = ~active | hit | blocked
            self.pose[rollback] = old_pose[rollback]
            # Keep digging articulation/boom active at a material stop, but roll
            # back all moving geometry on a wall/obstacle collision.
            self.joints[~active | hit] = old_joints[~active | hit]
            self.wheel_angles[rollback] = old_wheels[rollback]
            self.speed[rollback] = 0
            geometry = components(self.pose, self.joints)
            usable = active & ~hit
            travel = np.maximum(0, np.sum((geometry["mouth"]-last_mouth)*geometry["front_forward"], axis=1))
            curl = np.maximum(self.joints[:, 2]-old_joints[:, 2], 0)
            fraction = np.clip(travel/0.6 + curl*1.5, 0, 1) * usable
            room = np.minimum(self.loader.payload_kg-self.payload, 1200*dt)
            gain, cells = self.pile.extract(geometry["mouth"], geometry["front_forward"],
                                          geometry["bucket_height"], room, fraction)
            self.payload += gain
            loaded += gain
            removed_cells += cells
            delivered, spilled = release_material(self.payload, self.joints[:, 2],
                                                  geometry["mouth"], self.receiver,
                                                  self.receiver_half, dt)
            delivered *= usable
            spilled *= usable
            self.payload -= delivered + spilled
            self.delivered += delivered
            self.spilled += spilled
            self.peak_load = np.maximum(self.peak_load, self.payload)
            distance = np.linalg.norm(self.pose[:, :2]-old_pose[:, :2], axis=1)
            # Includes a low-speed hydraulic/drive proxy, explicitly not fuel.
            work = np.abs(drive)*np.maximum(distance, np.abs(controls[:, 0])*0.01*dt)
            work += np.sum(np.abs(self.joints-old_joints), axis=1)*1500
            self.effort += work*usable
            self.slip_s += slip*dt*usable
            self.last_slip[usable] = slip[usable]
            self.elapsed += dt*active
            immobile = usable & (np.abs(controls[:, 0]) > 0.4) & (np.abs(self.speed) < 0.03) & (np.max(np.abs(controls[:, 1:]), axis=1) < 0.1)
            self.stuck_time = np.where(immobile, self.stuck_time+dt, 0)
            success = usable & (self.delivered >= self.scene.success_kg)
            stuck = usable & ~success & (self.stuck_time+1e-12 >= self.scene.stuck_s)
            self.terminated |= success | stuck
            self.reason[success] = "success"
            self.reason[stuck] = "stuck"
            last_mouth = geometry["mouth"].copy()
        self.steps += 1
        self.truncated = (self.steps >= self.scene.max_steps) & ~self.terminated
        self.reason[self.truncated] = "time_limit"
        self._assert_finite()
        self._update_observations(np.ones(self.num_envs, dtype=bool))
        terms = {"delivered_kg": self.delivered-before_delivered,
                 "spilled_kg": self.spilled-before_spilled,
                 "effort_proxy_j": self.effort-before_effort,
                 "slip_s": self.slip_s-before_slip,
                 "elapsed_s": self.elapsed-before_elapsed,
                 "collision_count": (self.collision_time >= 0).astype(float)}
        reward, reward_description = calculate(terms, self.reward_config)
        info = self.diagnostics()
        info["reward_description"] = reward_description
        info.update(reward_terms=terms, transfer={"loaded_kg": loaded,
                    "delivered_kg": terms["delivered_kg"].copy(),
                    "spilled_kg": terms["spilled_kg"].copy(),
                    "position_xy_m": last_mouth.copy(), "removed_cell_kg": removed_cells})
        return self.observe(), reward, self.terminated.copy(), self.truncated.copy(), info

    def _assert_finite(self):
        for value in (self.pose, self.joints, self.speed, self.wheel_angles,
                      self.payload, self.delivered, self.spilled, self.effort,
                      self.slip_s, self.pile.height):
            if not np.isfinite(value).all():
                raise FloatingPointError("non-finite simulator state")
        ledger = self.pile.mass()+self.payload+self.delivered+self.spilled
        if not np.allclose(ledger, self.pile.initial_mass, rtol=0, atol=1e-7):
            raise FloatingPointError("material ledger diverged")

    def diagnostics(self):
        geometry = {k: v.copy() for k, v in components(self.pose, self.joints).items()}
        return {"pose": self.pose.copy(), "joints": self.joints.copy(),
                "speed_m_s": self.speed.copy(), "wheel_angle_rad": self.wheel_angles.copy(),
                "geometry": geometry, "pile_height_m": self.pile.height.copy(),
                "pile_origin_xy_m": self.pile.origin.copy(), "pile_density_kg_m3": self.pile.density.copy(),
                "episode_index": self.episode_index.copy(), "stream_id": self.stream_ids.copy(),
                "metrics": {"delivered_kg": self.delivered.copy(), "carried_kg": self.payload.copy(),
                            "spilled_kg": self.spilled.copy(), "pile_kg": self.pile.mass(),
                            "initial_kg": self.pile.initial_mass.copy(),
                            "fill_ratio": self.peak_load/self.loader.payload_kg,
                            "cycle_s": self.elapsed.copy(), "effort_proxy_j": self.effort.copy(),
                            "slip_s": self.slip_s.copy(), "reason": self.reason.copy(),
                            "collision_time_s": self.collision_time.copy(),
                            "impact_speed_m_s": self.impact_speed.copy()}}

    def scenario_identity(self):
        """Hash realised initial conditions, not just the nominal family name."""
        return [hashlib.sha256(canonical_json({
            "seed": int(self.seeds[i]), "stream_id": int(self.stream_ids[i]),
            "episode_index": int(self.episode_index[i]), "loader": self.loader.digest(),
            "scene": self.scene.digest(), "pile_origin": self.pile.origin[i].tolist(),
            "density_kg_m3": float(self.pile.density[i]),
            "initial_mass_kg": float(self.pile.initial_mass[i]),
            "initial_pile_sha256": self.initial_pile_hashes[i],
            "initial_pose": self.initial_pose[i].tolist(),
            "friction": float(self.friction[i]), "grade_rad": float(self.grade[i]),
            "half_width_m": float(self.half_width[i]), "resistance_n_m": float(self.resistance[i]),
        }).encode()).hexdigest() for i in range(self.num_envs)]
