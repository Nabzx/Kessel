"""Uncalibrated force limits, material transfer and conservative clearance."""

import numpy as np

from .kinematics import components, footprints


def traction(pose, speed, joints, payload, command, pile, friction, grade,
             resistance, acceleration_limit):
    geometry = components(pose, joints)
    contact_height = np.maximum(pile.sample(geometry["mouth"]) - geometry["bucket_height"], 0)
    mass = 10500.0 + payload
    requested = command * np.minimum(22000.0, 28000.0 / np.maximum(np.abs(speed), 0.5))
    grip = friction * mass * 9.81 * np.cos(grade)
    drive = np.clip(requested, -grip, grip)
    slope = mass * 9.81 * np.sin(grade) * np.cos(pose[:, 2])
    free_force = drive - slope
    direction = np.where(np.abs(speed) > 0.01, np.sign(speed), np.sign(free_force))
    rolling = 0.02 * mass * 9.81 * np.cos(grade)
    digging = resistance * contact_height * (direction > 0)
    drag = rolling + digging
    net = free_force - direction * drag
    stationary = np.abs(speed) <= 0.01
    # Static resistance cannot propel a resting machine backwards.
    net = np.where(stationary & (np.abs(free_force) <= drag), 0.0, net)
    acceleration = np.clip(net / mass, -acceleration_limit, acceleration_limit)
    slip = np.maximum(np.abs(requested) - grip, 0) / np.maximum(np.abs(requested), 1)
    return acceleration, slip, drive, contact_height


def clearance(old_pose, old_joints, pose, joints, half_width, ceiling,
              obstacles, x_min=-11.0, x_max=18.0):
    """Swept component AABBs, padded for rotational arcs between endpoints.

    Conservatively stops some clear manoeuvres. Obstacles are vertical boxes;
    this reference does not certify continuous 3D collision detection.
    """
    old, new = footprints(old_pose, old_joints), footprints(pose, joints)
    rear_delta = (pose[:, 2] - old_pose[:, 2] + np.pi) % (2*np.pi) - np.pi
    front_delta = rear_delta + joints[:, 0] - old_joints[:, 0]
    angle = np.stack((rear_delta, front_delta, front_delta), axis=1)
    # Include the rear-to-joint lever arm and bucket reach, not just box radii.
    padding = 8.0 * angle**2 / 8 + 1e-10
    low = np.minimum(old.min(axis=2), new.min(axis=2)) - padding[..., None]
    high = np.maximum(old.max(axis=2), new.max(axis=2)) + padding[..., None]
    reason = np.full(len(pose), "", dtype="U48")
    wall = ((low[..., 0] < x_min) | (high[..., 0] > x_max)
            | (low[..., 1] < -half_width[:, None])
            | (high[..., 1] > half_width[:, None])).any(axis=1)
    reason[wall] = "tunnel_wall"
    bucket_top = components(pose, joints)["bucket_height"] + 0.6
    old_top = components(old_pose, old_joints)["bucket_height"] + 0.6
    roof = np.maximum(np.maximum(bucket_top, old_top), 1.9) > ceiling
    reason[roof & (reason == "")] = "tunnel_roof"
    for i, (xmin, xmax, ymin, ymax) in enumerate(obstacles):
        hit = ((low[..., 0] <= xmax) & (high[..., 0] >= xmin)
               & (low[..., 1] <= ymax) & (high[..., 1] >= ymin)).any(axis=1)
        reason[hit & (reason == "")] = f"obstacle_{i}"
    return reason


def release_material(payload, curl, mouth, receiver, receiver_half, dt):
    tipping = np.clip((-curl - 0.2) / 0.5, 0, 1)
    released = payload * np.minimum(1, 3*dt*tipping)
    inside = (np.abs(mouth - receiver) <= receiver_half).all(axis=1)
    delivered = np.where(inside, released, 0)
    return delivered, released - delivered
