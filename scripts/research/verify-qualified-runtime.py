#!/usr/bin/env python3
"""ADR-0072: bounded in-process regression on consumed practice traces only."""
import copy
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"training"))
from kessel_lab.bootstrap_runtime import FAMILIES, METHOD, Session, SOURCES, control_status
from kessel_lab.range_pilot import weights
from kessel_training.controller import ReferenceController
from kessel_training.policy import configure_cpu

D = ROOT/"docs/phase-11/qualified-runtime-evidence"
PRACTICE = ROOT/"docs/phase-11/bootstrap-hold-evidence"


def sha(raw): return hashlib.sha256(raw).hexdigest()
def encoded(value): return json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False).encode()


def execute():
    configure_cpu(7,threads=1); started = time.monotonic(); D.mkdir(exist_ok=False)
    paths = [Path(__file__).resolve(),ROOT/"docs/adr/0072-qualified-stopping-live-simulator.md",
             ROOT/"training/kessel_lab/bootstrap_runtime.py",ROOT/"training/tests_lab/test_bootstrap_runtime.py",
             ROOT/"scripts/tests/qualified-client.test.mjs"]
    paths += sorted((ROOT/"docs/phase-11/qualified-demo").glob("*"))
    files = {str(p.relative_to(ROOT)):sha(p.read_bytes()) for p in paths if p.is_file()}
    plan = {"protocol":"ADR-0072","role":"consumed practice regression; no new qualification",
            "seed":19000,"cpu_threads":1,"evaluation_cap":9000,"wall_cap_s":120,"files":files,
            "commit":subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),
            "sources":list(SOURCES),"families":list(FAMILIES),
            "reference_archive_sha256":sha((PRACTICE/"traces.zip").read_bytes()),
            "reference_report_sha256":sha((PRACTICE/"report.json").read_bytes())}
    (D/"plan.json").write_text(json.dumps(plan,indent=2)+"\n")
    report = {"plan":plan,"cases":[],"complete":False,"budget_stop":None,"errors":[],
              "environment_decisions":0,"neural_queries":0,"teacher_queries":0,"optimiser_updates":0,
              "held_out_cases":0,"browser_sessions":0,"listening_servers":0}
    original = ReferenceController.act
    def reject(*args,**kwargs): raise AssertionError("teacher/reference call")
    ReferenceController.act = reject
    def budget():
        if time.monotonic()-started >= 120: raise TimeoutError("wall_cap")
        if report["environment_decisions"] >= 9000: raise TimeoutError("evaluation_cap")
    try:
        session = Session(); practice = json.loads((PRACTICE/"report.json").read_text())
        with zipfile.ZipFile(PRACTICE/"traces.zip") as archive:
            for source in SOURCES:
                for family in FAMILIES if source.startswith(METHOD) else ("healthy",):
                    budget(); initial = session.reset({"family":family,"source":source,"seed":19000})
                    assert initial["outcome"]["decisions"] == 0 and initial["telemetry"]["status"] == "ready"
                    assert session.run.injector.started is None and session.run.base.records == []
                    assert not initial["playback"]["running"] and not initial["playback"]["finished"]
                    method = initial["method"]; policy = "phase_memory-"+source.rsplit("-",1)[1]
                    reference = next(c for c in practice["cases"] if c["source"] == policy and c["method"] == method and c["pattern"] == family)
                    raw = archive.read(reference["trace"]); assert sha(raw) == reference["sha256"]
                    expected = json.loads(gzip.decompress(raw)); live = session.run
                    before = weights(live.base.actor)
                    # Both automatic stepping and paused single decisions use the same physics path.
                    session.play({"run_id":session.run_id,"after":0})
                    modes = set(); stale_checked = False
                    while not live.finished:
                        budget(); after = live.base.decisions
                        automatic = session.playing
                        next_state = session.step({"run_id":session.run_id,"after":after,"steps":1,
                            "automatic":automatic,"playback_epoch":session.epoch})
                        report["environment_decisions"] += 1; report["neural_queries"] += 1
                        record = live.base.records[-1]; modes.add(control_status(record))
                        telemetry = next_state["telemetry"]
                        assert telemetry["applied_action"] == record["action"]
                        assert telemetry["input_time_s"] == record["t_s"] < next_state["frames"][-1]["t_s"]
                        if record["supervision"]:
                            assert telemetry["neural_proposal"] == record["supervision"]["neural_proposal"]
                            assert telemetry["sensor"]["usable"] == record["supervision"]["health"]["usable"]
                        if after == 12:
                            old_epoch = session.epoch; snapshot = copy.deepcopy(live.base.records)
                            paused = session.pause({"run_id":session.run_id})
                            assert live.base.records == snapshot and paused["outcome"]["decisions"] == 13
                            try: session.step({"run_id":session.run_id,"after":13,"automatic":True,"playback_epoch":old_epoch})
                            except ValueError: stale_checked = True
                            else: raise AssertionError("stale automatic step accepted")
                        elif after == 13: session.play({"run_id":session.run_id,"after":14})
                    assert stale_checked and before == weights(live.base.actor)
                    assert live.base.records == expected["frames"][:-1],(source,family,"decision trace differs")
                    final = live.frame()
                    assert {k:final[k] for k in expected["frames"][-1]} == expected["frames"][-1]
                    assert live.base.outcome() == expected["outcome"]
                    evaluation = live.evaluation()
                    assert evaluation["passed"] == reference["criterion_passed"]
                    assert evaluation["stop"] == reference["stop"]
                    assert evaluation["override_decisions"] == reference["override_decisions"]
                    assert evaluation["resumed"] == reference["resumed"]
                    assert evaluation["trigger_reached"] == reference["trigger_reached"]
                    if family in ("carry_loss","partial_carry_zeroed"):
                        assert live.end_reason == "hold_window_passed" and not live.base.done
                        assert not live.base.outcome()["full_success"]
                    paused = session.pause({"run_id":session.run_id}); previous = encoded(live.base.records)
                    exported = session.export_trace()
                    assert len(exported["frames"]) == live.base.decisions+1
                    assert encoded(live.base.records) == previous and not exported["applied_machine_commands"]
                    assert not exported["playback"]["running"] and exported["playback"]["finished"]
                    assert exported["identity"] == initial["identity"]
                    projected = live.base.records+[{k:final[k] for k in expected["frames"][-1]}]
                    row = {"source":source,"family":family,"seed":19000,"method":method,"decisions":live.base.decisions,
                           "checkpoint_sha256":live.base.checkpoint_sha256,"trace":reference["trace"],"reference_sha256":reference["sha256"],
                           "frame_sha256":sha(encoded(projected)),"outcome":live.base.outcome(),"evaluation":evaluation,
                           "modes":sorted(modes),"end_reason":live.end_reason,"weights_unchanged":True,"exact":True}
                    report["cases"].append(row)
                    if source == SOURCES[0] and family == "recovery":
                        export_raw = gzip.compress(encoded(exported),mtime=0)
                        (D/"recovery-export.json.gz").write_bytes(export_raw)
                        report["retained_export_sha256"] = sha(export_raw)
                    print(source,family,live.base.decisions,"decisions; exact",flush=True)
        # A new selection must clear the prior observer, fault trigger, task clock and log.
        old = session.run
        old_id = session.run_id; previous = encoded(old.base.records)
        initial = session.reset({"source":SOURCES[0],"family":"recovery","seed":19000})
        assert session.run_id != old_id and encoded(old.base.records) == previous
        actor = session.run.base.actor
        assert actor.previous_motion is None and actor.disturbance == 0 and not actor.estimate_valid
        assert session.run.injector.started is None and not session.run.base.records
        assert initial["telemetry"]["input_time_s"] == initial["telemetry"]["task_time_s"] == 0
        try: session.step({"run_id":old_id,"after":old.base.decisions})
        except ValueError: pass
        else: raise AssertionError("replaced run accepted")
        report.update(complete=len(report["cases"]) == 15,qualification_sha256=session.qualification_sha,
                      runtime_sha256=session.runtime_sha,reset_cleared=True,exports_nonmutating=True)
    except TimeoutError as error:
        report["budget_stop"] = str(error)
    except Exception as error:
        report["errors"].append(type(error).__name__+": "+str(error))
    finally:
        ReferenceController.act = original
        report["active_wall_s"] = time.monotonic()-started
        (D/"report.json").write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
    print("Complete",report["complete"],"decisions",report["environment_decisions"],"wall",round(report["active_wall_s"],3),"errors",report["errors"],"budget",report["budget_stop"])
    if not report["complete"] or report["errors"] or report["budget_stop"]: raise SystemExit(1)


if __name__ == "__main__": execute()
