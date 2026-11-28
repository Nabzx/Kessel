"""Frozen practice and audited fresh synthetic qualification, with separate gates."""
import argparse
import json
import zipfile

import numpy as np

from kessel_training.policy import configure_cpu
from kessel_training.wm_data import write_archive
from kessel_training.wm_evaluate import metrics, open_loop
from kessel_training.wm_state import pack
from .forecast_refit import operational_gate
from .harvest_contract import certificate, summary
from .linear_feedback import load as load_feedback
from .runtime import ROOT, FAMILIES
from .harvest_scenarios import environment
from .start_rollout import run
from .structured_data import arrays, collect_fixture, fixture
from .structured_fit import load as load_forecast
from .study_tools import Budget, begin, retain, seal, sha

PATTERNS = ("recovery","carry_loss","stale_clearance","old_clearance","missing_clearance")
SOURCES = ("reference","learned_linear")
SEEDS = tuple(range(207400,207432))
D = ROOT/"docs/phase-11/harvest-qualification-evidence"


def execute(fresh):
    configure_cpu(7,threads=1)
    directory = D/"fresh" if fresh else ROOT/"docs/phase-11/harvest-practice-evidence"
    budget = Budget(900 if fresh else 180,environment=100000 if fresh else 12000,teacher=100000 if fresh else 12000,replay=100000 if fresh else 12000)
    reservation = None
    if fresh:
        reservation = json.loads((D/"reservation.json").read_text())
        if not reservation["verified"] or reservation["seeds"] != list(SEEDS) or reservation["hits"] or reservation["errors"]: raise ValueError("verified unused bases required")
        for name,digest in reservation["audit_files"].items():
            if sha((ROOT/name).read_bytes()) != digest: raise ValueError("changed audit source")
        practice = json.loads((ROOT/"docs/phase-11/harvest-practice-evidence/report.json").read_text())
        if not practice["complete"] or not practice["supported_envelope_gate"]: raise ValueError("practice envelope gate required")
        for name,digest in practice["plan"]["files"].items():
            if sha((ROOT/name).read_bytes()) != digest: raise ValueError("candidate changed after practice")
    checkpoint = ROOT/"docs/phase-11/linear-feedback-evidence/feedback.pt"
    model_path = ROOT/"docs/phase-11/structured-dynamics-evidence/structured.pt"
    forecast_report = ROOT/"docs/phase-11/structured-dynamics-evidence/report.json"
    paths = [str(p.relative_to(ROOT)) for p in (ROOT/"training/kessel_training").glob("*.py")]
    paths += ["training/kessel_lab/"+n+".py" for n in ("harvest_task","start_progress","start_rollout","harvest_contract","harvest_qualification","linear_feedback",
        "progress_task","progress_supervisor","runtime","clearance_stop","bootstrap_hold","range_contract","range_supervisor","motion_hold","range_pilot",
        "structured_data","structured_model","structured_fit","forecast_refit","forecast_dataset","reserve_harvest","harvest_scenarios")]
    selected = reservation["selected_by_family"] if fresh else {f:[19025] for f in FAMILIES}
    jobs = [(source,family,None,seed,"fresh" if fresh else "practice") for family in FAMILIES for seed in selected[family] for source in SOURCES]
    jobs += [(source,"nominal",pattern,seed,"fresh" if fresh else "practice") for seed in selected["nominal"] for pattern in PATTERNS for source in SOURCES]
    if fresh: jobs += [(source,"prepared_no_progress",None,seed,"start_guard_challenge") for seed in range(207470,207478) for source in SOURCES]
    if not fresh: jobs += [(source,family,None,seed,"known_regression") for source in SOURCES for family,seed in (("low",19023),("low_grip",19021),("low_grip",19024))]
    plan = begin(directory,"docs/adr/0084-frozen-harvest-and-forecast-qualification.md",paths,
        {"kind":"frozen-harvest-qualification-v1","fresh":fresh,"jobs":jobs,"feedback_sha256":sha(checkpoint.read_bytes()),"forecast_sha256":sha(model_path.read_bytes()),
         "forecast_report_sha256":sha(forecast_report.read_bytes()),"reservation_sha256":sha((D/"reservation.json").read_bytes()) if fresh else None,
         "refusal_acceptance":"pending; original delivery gate retained","artifact_cap_bytes":96*1024**2})
    report = {"plan":plan,"cases":[],"fixtures":[],"complete":False,"errors":[],"budget_stop":None,"runtime_admitted":False,
              "weight_updates":0,"evaluation_label_queries":0,"forecast_assisted_actions":0}
    episodes = []
    try:
        with zipfile.ZipFile(directory/"traces.zip","w",compression=zipfile.ZIP_STORED) as archive:
            for index,(source,family,pattern,seed,split) in enumerate(jobs):
                initial,_ = environment(family,seed); initial_state = pack(initial)[0]; proof = certificate(initial_state)
                if fresh:
                    reserved, = [r for r in reservation["identities"] if r["seed"] == seed and r["family"] == family]
                    if sha(initial_state.astype("<f8").tobytes()) != reserved["fingerprints"]["state<f8"]: raise ValueError("reserved initial state changed")
                model,_ = load_feedback(checkpoint); learned = source == "learned_linear"
                value = run(family,seed,budget,pattern,replay=True,actuator=model.action if learned else None)
                calls = sum(f["supervision"]["proposal_source"] == "learned_linear_feedback" and not f["supervision"]["override"] for f in value["frames"][:-1]) if learned else 0
                if model.calls != 2*calls: raise AssertionError("actual network query count differs")
                value.update(neural_queries=calls,action_replay_queries=calls,checkpoint_sha256=plan["feedback_sha256"] if learned else None)
                if value["frames"][0]["state"] != initial_state.tolist(): raise ValueError("initial certificate mismatch")
                row = {"source":source,"family":family,"pattern":pattern,"seed":seed,"split":split,"certificate":proof,
                       "outcome":value["outcome"],"evaluation":value["evaluation"],"neural_queries":calls,
                       **retain(archive,f"{index:03}-{source}-{family}-{pattern or 'standard'}-{seed}.json.gz",value)}
                report["cases"].append(row)
                if learned and split != "known_regression" and pattern is None: episodes.append(value)
                print("fresh" if fresh else "practice",source,family,pattern,seed,value["evaluation"]["passed"],"supported",row["certificate"]["supported"],flush=True)
            if fresh:
                for kind,seeds in (("collision",range(207450,207458)),("stuck",range(207458,207466))):
                    for seed in seeds:
                        initial = fixture(kind,seed)
                        reserved, = [r for r in reservation["identities"] if r["seed"] == seed and r["family"] == "prepared_"+kind]
                        if sha(pack(initial)[0].astype("<f8").tobytes()) != reserved["fingerprints"]["state<f8"]: raise ValueError("prepared reservation mismatch")
                        value = collect_fixture(kind,seed,budget); episodes.append(value)
                        report["fixtures"].append({"family":"prepared_"+kind,"seed":seed,"outcome":value["outcome"],"fixture_gate_passed":value["fixture_gate_passed"],
                            **retain(archive,f"fixture-{kind}-{seed}.json.gz",value)})
        report["groups"] = summary(report["cases"],fresh)
        report["original_full_gate"] = all(c["evaluation"]["passed"] for c in report["cases"])
        known = [c for c in report["cases"] if c["split"] == "known_regression" and (c["family"],c["seed"]) != ("low_grip",19024)]
        report["supported_envelope_gate"] = bool(all(g["passed"] for g in report["groups"]) and all(c["evaluation"]["passed"] for c in known) and not any(c["outcome"]["collision"] for c in report["cases"]))
        report["max_replay_state_error"] = 0.
        challenges = [c for c in report["cases"] if c["split"] == "start_guard_challenge"]
        report["start_guard_qualified"] = bool(fresh and len(challenges) == 16 and all(c["evaluation"]["proposed_refusal"] and c["evaluation"]["proposed_refusal"]["passed"] for c in challenges))
        if fresh:
            data,metadata = arrays(episodes); write_archive(directory/"forecast-data.npz",data)
            model,_ = load_forecast(model_path); predicted = model.predict(data["state"],data["action"])
            write_archive(directory/"forecast-predictions.npz",{k:v for k,v in predicted.items() if k in ("next_state","reward","events","disagreement")})
            gate = json.loads(forecast_report.read_text())["methods"]["structured"]["calibration_gate"]
            families = []
            for family in (*FAMILIES,"prepared_collision","prepared_stuck","prepared_no_progress"):
                ids = [e["id"] for e in metadata if e["family"] == family]; mask = np.isin(data["episode_id"],ids)
                families.append({"family":family,**operational_gate(model,{k:v[mask] for k,v in data.items()},gate)})
            report["forecast"] = {"episodes":metadata,"rows":len(data["state"]),"calibration_gate":gate,"one_step":metrics(predicted,data),
                "drift":open_loop(model,data,metadata,max_windows=128),"families":families,
                "gate_passed":bool(gate["supported_horizon"] >= 1 and all(r["forecast_gate"]["accepted"] and r["operational_accepted"] and
                    r["forecast_gate"]["accepted_high_error_fraction"] <= .1 and r["operational_high_error_fraction"] <= .1 for r in families if r["family"] != "blocked"))}
        report["complete"] = len(report["cases"]) == len(jobs) and (not fresh or len(report["fixtures"]) == 16)
        if sum(p.stat().st_size for p in directory.rglob("*") if p.is_file()) > 96*1024**2: raise TimeoutError("artifact_cap")
        if sha(checkpoint.read_bytes()) != plan["feedback_sha256"] or sha(model_path.read_bytes()) != plan["forecast_sha256"]: raise AssertionError("weights changed")
    except TimeoutError as error: report["budget_stop"] = str(error)
    except Exception as error: report["errors"].append(type(error).__name__+": "+str(error))
    report["cost"] = budget.report(); seal(directory,report)
    print("qualification",fresh,"complete",report["complete"],"envelope",report.get("supported_envelope_gate"),"forecast",report.get("forecast",{}).get("gate_passed"),report["errors"],report["budget_stop"],report["cost"],flush=True)
    if not report["complete"] or report["errors"] or report["budget_stop"]: raise SystemExit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--fresh",action="store_true"); execute(parser.parse_args().fresh)
