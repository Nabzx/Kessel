/** Request-driven playback. No browser globals, timers or automatic physics. */
export class SimulationClient {
  constructor(request, changed = () => {}) {
    this.request = request; this.changed = changed; this.state = null;
    this.generation = 0; this.controlVersion = 0; this.desiredRunning = false;
    this.resetToken = null; this.stepToken = null; this.controls = new Set();
  }
  get controlBusy() { return this.controls.size > 0; }
  get playing() { return this.desiredRunning && !!this.state?.playback.running && !this.state?.playback.finished && !this.controlBusy && !this.resetToken; }
  get canStep() { return !!this.state && !this.state.playback.finished && !this.state.playback.running && !this.desiredRunning && !this.resetToken && !this.stepToken && !this.controlBusy; }
  accept(next, generation, reset = false) {
    if (generation !== this.generation) return false;
    if (!reset && this.state && (next.run_id !== this.state.run_id || next.playback.epoch < this.state.playback.epoch || next.outcome.decisions < this.state.outcome.decisions)) return false;
    this.state = next;
    if (next.playback.finished) this.desiredRunning = false;
    this.changed(); return true;
  }
  async reset(selection) {
    if (this.resetToken) return null;
    const token = {}; const generation = ++this.generation;
    this.controlVersion++; this.desiredRunning = false; this.controls.clear(); this.stepToken = null; this.resetToken = token; this.changed();
    try {
      const next = await this.request('/api/reset', selection);
      this.accept(next, generation, true); return this.state;
    } finally { if (this.resetToken === token) this.resetToken = null; this.changed(); }
  }
  async control(action) {
    if (!this.state || this.resetToken) return null;
    if (action === 'play' && this.state.playback.finished) throw Error('Run finished. Start a new run.');
    const generation = this.generation, version = ++this.controlVersion, token = {};
    this.desiredRunning = action === 'play'; this.controls.add(token); this.changed();
    try {
      const next = await this.request(`/api/${action}`, {run_id:this.state.run_id, after:this.state.outcome.decisions});
      this.accept(next, generation); return this.state;
    } catch (error) {
      if (generation !== this.generation || version !== this.controlVersion) return null;
      this.desiredRunning = false; throw error;
    } finally { this.controls.delete(token); this.changed(); }
  }
  play() { return this.control('play'); }
  pause() { return this.control('pause'); }
  async step(count = 1, automatic = false) {
    if (!this.state || this.resetToken || this.stepToken || this.state.playback.finished) return null;
    if (automatic && !this.playing) return null;
    if (!automatic && !this.canStep) throw Error('Pause before stepping manually.');
    const generation = this.generation, version = this.controlVersion, token = {};
    const current = this.state; this.stepToken = token; this.changed();
    try {
      const next = await this.request('/api/step', {run_id:current.run_id, after:current.outcome.decisions, steps:count,
        automatic, playback_epoch:current.playback.epoch});
      this.accept(next, generation); return this.state;
    } catch (error) {
      if (generation !== this.generation || version !== this.controlVersion) return null;
      this.desiredRunning = false; throw error;
    } finally { if (this.stepToken === token) this.stepToken = null; this.changed(); }
  }
  async exportTrace() {
    if (!this.state) return null;
    const generation = this.generation;
    if (this.state.playback.running || this.desiredRunning || this.controlBusy) await this.pause();
    if (generation !== this.generation) return null;
    const runId = this.state.run_id;
    const trace = await this.request('/api/export');
    if (generation !== this.generation) return null;
    if (trace.run_id !== runId) throw Error('Run was replaced. Start a new run.');
    return trace;
  }
}
