// Pure recorded-data adapter. No rendering, training or invented samples.
const sha = (v) => typeof v === "string" && /^[a-f0-9]{64}$/.test(v);
const need = (condition, message) => { if (!condition) throw new Error(message); };
const finite = (value) => {
  if (typeof value === "number") need(Number.isFinite(value), "Non-finite experiment value");
  else if (Array.isArray(value)) value.forEach(finite);
  else if (value && typeof value === "object") Object.values(value).forEach(finite);
};
export function validateBundle(bundle) {
  finite(bundle);
  need(bundle.schema_version === "1.0" && bundle.source_mode === "recorded_synthetic", "Unsupported experiment source");
  need(bundle.units.position === "m" && bundle.units.angle === "rad" && bundle.units.mass === "kg" && bundle.units.time === "s" && bundle.units.action === "normalised [-1,1]", "Experiment units differ");
  need(bundle.state_names.length === 102 && bundle.state_names[0] === "x_m" && bundle.state_names[15] === "pile_0_0_m" && bundle.state_names[79] === "pile_origin_x_m", "Unsupported physical state");
  need(sha(bundle.run.configuration_sha256) && sha(bundle.run.source.package_sha256) && bundle.run.source.training_dirty === false && bundle.export_source.training_dirty === false, "Unverified experiment provenance");
  need(sha(bundle.world_model.model_sha256) && bundle.world_model.kind === "raw_neural_ensemble", "Unidentified prediction model");
  need(bundle.episodes.length === 3 && bundle.presentation.replay_seconds === 12 && bundle.presentation.checkpoint_seconds === 4, "Unsupported replay schedule");
  let steps = 0;
  for (const point of bundle.learning_curve) {
    need(point.environment_steps > steps, "Non-monotonic training log"); steps = point.environment_steps;
  }
  need(steps === bundle.run.counters.environment_steps, "Training counters differ");
  for (const episode of bundle.episodes) {
    need(sha(episode.policy.checkpoint_sha256) && sha(episode.policy.source_checkpoint_sha256), "Executed checkpoint identity missing");
    need(episode.terminated !== episode.truncated && episode.records.length === episode.steps + 1 && episode.records.length <= 2001, "Episode boundary missing");
    need(episode.records[0].t_s === 0 && episode.records.at(-1).action === null, "Episode endpoints differ");
    let previous = -1;
    episode.records.forEach((row, index) => {
      need(row.t_s > previous && row.state.length === 102 && row.observation.length === 65 && row.wheel_angles_rad.length === 4, "Invalid record shape/time");
      need(Math.abs(row.t_s - row.state[10]) < 1e-9, "State clock differs"); previous = row.t_s;
      if (index < episode.steps) need(row.action?.length === 4 && row.action.every((v) => Math.abs(v) <= 1) && Number.isFinite(row.reward), "Invalid recorded action/reward");
      if (index < episode.steps) need(Math.abs(Object.values(row.reward_weighted).reduce((a, b) => a + b, 0) - row.reward) < 1e-9, "Reward contributions differ");
      else need(row.reward === null, "Terminal record has a next reward");
      for (const prediction of row.predictions) {
        need([1, 2, 4, 8].includes(prediction.horizon_decisions), "Invalid forecast horizon");
        if (prediction.prediction === null) {
          need(prediction.residual === null && typeof prediction.missing_reason === "string", "Invented missing prediction"); continue;
        }
        const target = index + prediction.horizon_decisions, reference = episode.records[target];
        need(reference && prediction.reference_index === target && prediction.target_t_s === reference.t_s && prediction.prediction.length === 102, "Forecast crosses reference boundary");
        const p = prediction.prediction;
        need(Math.abs(Math.hypot(p[0] - reference.state[0], p[1] - reference.state[1]) - prediction.residual.position_m) < 1e-9, "Prediction residual differs");
        need(Math.abs(p[7] - reference.state[7] - prediction.residual.carried_kg) < 1e-9, "Material residual differs");
        need(prediction.members_xy_m.length === 3 && prediction.members_xy_m.every((v) => v.length === 2), "Ensemble endpoints missing");
        const reward = episode.records.slice(index, target).reduce((sum, r) => sum + r.reward, 0);
        need(Math.abs(prediction.cumulative_reward - reward - prediction.residual.reward) < 1e-9, "Reward residual differs");
      }
    });
  }
  return bundle;
}

export async function loadExperiment(url = "data/experiments/index.json", fetcher = fetch) {
  const response = await fetcher(url);
  need(response.ok, "Recorded experiment catalogue unavailable");
  const catalogue = await response.json(), entry = catalogue.experiments?.[0];
  need(catalogue.schema_version === "1.0" && entry?.source_mode === "recorded_synthetic" && sha(entry.sha256) && entry.url?.startsWith("data/experiments/") && !entry.url.includes(".."), "Invalid experiment catalogue");
  need(entry.bytes > 0 && entry.bytes <= 8 * 1024 * 1024, "Experiment exceeds the playback budget");
  const asset = await fetcher(entry.url); need(asset.ok, "Recorded experiment bundle unavailable");
  const bytes = await asset.arrayBuffer(); need(bytes.byteLength === entry.bytes, "Experiment byte count differs");
  need(globalThis.crypto?.subtle, "Recorded playback requires HTTPS or localhost for integrity checks");
  const hash = [...new Uint8Array(await crypto.subtle.digest("SHA-256", bytes))].map((v) => v.toString(16).padStart(2, "0")).join("");
  need(hash === entry.sha256, "Experiment checksum differs");
  const bundle = validateBundle(JSON.parse(new TextDecoder().decode(bytes)));
  need(bundle.run_id === entry.run_id, "Experiment identity differs");
  return bundle;
}

export function sampleEpisode(episode, time) {
  const records = episode.records;
  let lo = 0, hi = records.length - 1;
  while (lo < hi) { const mid = Math.ceil((lo + hi) / 2); if (records[mid].t_s <= time + 1e-9) lo = mid; else hi = mid - 1; }
  const frame = records[lo], next = records[Math.min(lo + 1, records.length - 1)];
  const alpha = next.t_s > frame.t_s ? Math.max(0, Math.min(1, (time - frame.t_s) / (next.t_s - frame.t_s))) : 0;
  const pose = frame.state.slice(0, 7);
  for (const i of [0, 1, 3, 4, 5, 6]) pose[i] += (next.state[i] - pose[i]) * alpha;
  const angle = Math.atan2(Math.sin(next.state[2] - pose[2]), Math.cos(next.state[2] - pose[2])); pose[2] += angle * alpha;
  // Material, observations, actions, events and rewards remain at real boundaries.
  return { frame, next, index: lo, alpha, pose, wheelAngles: frame.wheel_angles_rad.map((v, i) => v + (next.wheel_angles_rad[i] - v) * alpha) };
}

export class ReplayClock {
  constructor(bundle, reduced = false) { this.bundle = bundle; this.reduced = reduced; this.pace = 1; this.replay(); }
  replay() { this.cursor = 0; this.paused = this.reduced; this.sequence = true; this.end = 12; }
  checkpoint(index) { need(Number.isInteger(index) && index >= 0 && index < 3, "Invalid checkpoint"); this.cursor = index * 4; this.end = (index + 1) * 4; this.sequence = false; this.paused = true; }
  seek(time) { const index = this.state().index, duration = this.bundle.episodes[index].records.at(-1).t_s; this.checkpoint(index); this.cursor += time >= duration ? 4 : Math.max(0, time) / duration * 3.65; }
  toggle() { if (this.cursor >= this.end) this.cursor = this.sequence ? 0 : this.end - 4; this.paused = !this.paused; }
  setPace(pace) { need([0.5, 1, 2].includes(pace), "Invalid playback pace"); this.pace = pace; }
  update(delta) { need(Number.isFinite(delta) && delta >= 0, "Invalid playback delta"); if (!this.paused) this.cursor = Math.min(this.end, this.cursor + delta * this.pace); if (this.cursor >= this.end) this.paused = true; return this.state(); }
  state() {
    const index = Math.min(2, this.sequence ? Math.floor(this.cursor / 4) : Math.round(this.end / 4) - 1);
    const episode = this.bundle.episodes[index], duration = episode.records.at(-1).t_s;
    const fraction = Math.min(1, Math.max(0, (this.cursor - index * 4) / 3.65));
    return { index, episode, time: duration * fraction, acceleration: duration / 3.65 * this.pace, holding: fraction === 1 && !this.paused, paused: this.paused, complete: this.cursor >= this.end };
  }
}

export function curvePoints(rows) {
  if (!rows.length) return [];
  const values = rows.map((r) => r.mean_step_reward), low = Math.min(...values), high = Math.max(...values), span = Math.max(1e-9, high - low);
  const maxSteps = rows.at(-1).environment_steps;
  return rows.map((r) => [r.environment_steps / maxSteps * 300, 66 - (r.mean_step_reward - low) / span * 60]);
}
