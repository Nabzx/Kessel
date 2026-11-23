"""Verify the receiver-frame diagnosis, pilot, fresh gate and exact-source replay."""
import gzip
import hashlib
import json
import math
from pathlib import Path
import struct
import zipfile

ROOT=Path(__file__).resolve().parents[1]
D=ROOT/"docs/phase-11/receiver-evidence"
METHOD="receiver_x_frame"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def verify():
    diagnosis=json.loads((D/"diagnosis.json").read_text())
    assert diagnosis["retained_cases"]==64 and diagnosis["training_acquisition_episodes"]==176
    assert diagnosis["counterfactual_policy_queries"]==72
    assert diagnosis["new_environment_decisions"]==diagnosis["teacher_queries"]==diagnosis["optimiser_updates"]==0
    assert diagnosis["wall_s"]<=45 and diagnosis["cpu_threads"]==1
    pilot=json.loads((D/"pilot.json").read_text())
    assert pilot["complete"] and len(pilot["cases"])==14
    assert pilot["held_out_cases"]==pilot["teacher_training_queries"]==pilot["optimiser_updates"]==0
    assert pilot["active_wall_s"]<=60 and pilot["environment_decisions"]<=8400
    assert sha((D/"pilot-traces.zip").read_bytes())==pilot["trace_archive_sha256"]
    cert=json.loads((D/"reservation.json").read_text())
    assert cert["verified"] and not cert["hits"] and not cert["errors"]
    assert cert["base"]["reservation_verified"] and not cert["base"]["hits"] and not cert["base"]["failures"]
    assert cert["seeds"]==list(range(205800,205808)) and cert["new_policy_queries"]==0
    supplement=json.loads((D/"zip-history.json").read_text())
    assert supplement["verified"] and not supplement["hits"]
    assert supplement["reservation_sha256"]==sha((D/"reservation.json").read_bytes())
    assert supplement["new_policy_queries"]==0 and supplement["wall_s"]<=supplement["cap_s"]==15
    report=json.loads((D/"qualification.json").read_text());plan=report["plan"]
    assert json.loads((D/"qualification-plan.json").read_text())==plan
    assert sha((D/"reservation.json").read_bytes())==plan["reservation_sha256"]
    assert report["complete"] and report["budget_stop"] is None
    assert report["active_wall_s"]<=420 and report["evaluation_decisions"]<=67200
    assert report["physics_replay_decisions"]<=28800
    assert report["adapted_physical_replay_cases"]==48 and report["learned_action_replay_cases"]==96
    assert report["max_state_error"]==report["max_action_error"]==0
    assert report["teacher_training_queries"]==report["optimiser_updates"]==0
    evaluation=json.loads((D/"qualification-evaluation.json").read_text())
    assert evaluation["cases"]==report["cases"] and evaluation["budget_stop"] is None
    assert evaluation["environment_decisions"]==report["evaluation_decisions"]
    expected={(f,seed,"phase_memory-"+str(p),m) for f in ("nominal","receiver_far")
              for seed in cert["seeds"] for p in (7,19,41) for m in ("original",METHOD)}
    expected|={(f,seed,"reference","reference") for f in ("nominal","receiver_far") for seed in cert["seeds"]}
    assert {(c["family"],c["seed"],c["source"],c["method"]) for c in report["cases"]}==expected
    assert len(report["cases"])==len(plan["cases"])==112
    assert sha((D/"qualification-traces.zip").read_bytes())==report["trace_archive_sha256"]
    assert sha((D/"qualification-source.zip").read_bytes())==report["source_archive_sha256"]
    selection=json.loads((ROOT/"docs/phase-11/phase-memory-evidence/selection.json").read_text())
    decisions=0;action_queries=0;physical_queries=0;max_mass=0.
    with zipfile.ZipFile(D/"qualification-traces.zip") as z:
        assert set(z.namelist())=={r["trace"] for r in report["cases"]}
        for case in report["cases"]:
            raw=z.read(case["trace"]);assert sha(raw)==case["sha256"]
            trace=json.loads(gzip.decompress(raw));frames=trace["frames"]
            assert trace["job"]=={k:case[k] for k in ("family","seed","source","method")}
            assert trace["identity"]==case["identity"] and trace["scenario"]==case["scenario"]
            assert trace["outcome"]=={k:case[k] for k in trace["outcome"]}
            assert case["done"] and case["weights_unchanged"] and case["initial_payload_kg"]==0
            checkpoint=None if case["source"]=="reference" else selection[case["source"]]["sha256"]
            assert checkpoint==case["checkpoint_sha256"]==trace["checkpoint_sha256"]
            assert len(frames)==case["decisions"]+1 and case["decisions"]<=600
            assert frames[0]["state"][7]==0 and frames[-1]["state"][8]==case["delivered_kg"]
            assert sha(struct.pack("<102d",*frames[0]["state"]))==case["scenario"]["initial_state_sha256"]
            assert case["full_success"]==(case["reason"]=="success")
            if case["full_success"]:assert case["delivered_kg"]>=2000 and not case["collision"]
            for index,frame in enumerate(frames):
                s=frame["state"];assert len(s)==102 and all(math.isfinite(x) for x in s)
                max_mass=max(max_mass,abs(sum(s[15:79])*.25*s[81]+sum(s[7:10])-s[82]))
                if index<len(frames)-1:
                    assert frame["next_state"]==frames[index+1]["state"]
                    assert len(frame["action"])==4 and all(math.isfinite(a) and abs(a)<=1 for a in frame["action"])
            decisions+=case["decisions"]
            if case["source"]!="reference":action_queries+=case["decisions"]
            if case["method"]==METHOD:physical_queries+=case["decisions"]
    assert max_mass<1e-7 and decisions==report["evaluation_decisions"]
    assert action_queries==report["action_replay_queries"] and physical_queries==report["physics_replay_decisions"]
    assert decisions-action_queries==report["reference_controller_queries"]
    passed=all(len(rows:=[c for c in report["cases"] if c["method"]==METHOD and
                         c["source"]=="phase_memory-"+str(p) and c["family"]==f])==8
               and sum(c["full_success"] for c in rows)>=7 and not any(c["collision"] for c in rows)
               for p in (7,19,41) for f in ("nominal","receiver_far"))
    assert report["admitted"]==passed
    for summary in report["summaries"]:
        rows=[c for c in report["cases"] if (c["family"],c["method"],c["source"])==
              (summary["family"],summary["method"],summary["source"])]
        assert len(rows)==summary["cases"]==8
        assert sum(c["full_success"] for c in rows)==summary["successes"]
        assert sum(c["collision"] for c in rows)==summary["collisions"]
    with zipfile.ZipFile(D/"qualification-source.zip") as z:
        for name,digest in plan["files"].items():assert sha(z.read(name))==digest
        digest=hashlib.sha256()
        for name in sorted(n for n in z.namelist() if n.startswith("training/kessel_training/") and n.endswith(".py")):
            digest.update(Path(name).name.encode());digest.update(z.read(name))
        assert digest.hexdigest()==plan["source"]["package_sha256"]
    manifest=json.loads((D/"files.json").read_text())
    for name,expected in manifest.items():
        p=(ROOT/name).resolve();assert p.is_relative_to(ROOT)
        assert sha(p.read_bytes())==expected,name
    print("PASS: receiver diagnosis, bounded pilot, 112 fresh cases, narrow admission and exact replay")


if __name__=="__main__":
    verify()
