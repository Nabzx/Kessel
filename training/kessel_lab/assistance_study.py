"""Frozen matched-budget hybrid assistance comparison; no method promotion."""
import copy
import json
import statistics
import zipfile

from kessel_training.policy import configure_cpu
from kessel_training.wm_state import pack
from .forecast_assistance import AssistanceController, CountedPredictor
from .harvest_admission import load_admission
from .harvest_contract import certificate
from .harvest_runtime import LiveRun
from .harvest_scenarios import environment
from .runtime import ROOT
from .study_tools import Budget, begin, retain, seal, write

D = ROOT/"docs/phase-11/assistance-comparison-evidence"
FAMILIES = ("nominal","low","ridge","rubble","steep","start_offset","low_grip","high_resistance","range_impaired","blocked")


def make_run(family,seed,pattern,enabled,admission,budget):
    run = LiveRun(family,seed,"learned_linear",pattern,admission,"experimental_assistance_study")
    run.forecaster = CountedPredictor(run.forecaster,budget)
    run.actor = AssistanceController(run.actor,run.env,run.forecaster,admission["forecast_gate"]["threshold"],enabled)
    return run


def execute():
    configure_cpu(7,threads=1); budget = Budget(600,environment=30000,replay=30000,model_rows=300000)
    admission = load_admission()
    paths = ["training/kessel_lab/"+name+".py" for name in ("forecast_assistance","assistance_study","harvest_runtime","harvest_admission","harvest_runtime_gate")]
    jobs = [(f,s,None) for s in (19020,19021) for f in FAMILIES]+[("nominal",s,p) for s in (19020,19021) for p in ("recovery","carry_loss")]
    screened = []
    for family,seed,pattern in jobs:
        env,_ = environment(family,seed); screened.append({"family":family,"seed":seed,"pattern":pattern,"certificate":certificate(pack(env)[0])})
    selected = [c for c in screened if c["certificate"]["supported"]]
    plan = begin(D,"docs/adr/0087-matched-forecast-control-assistance.md",paths,{"kind":"matched_hybrid_assistance_v1","admission":admission,"screened":screened,
        "arms":["shadow_only","candidate_refinement"],"max_physical_per_case":600,"max_replay_per_case":600,"max_model_rows_per_physical_or_replay_step":6})
    report = {"plan":plan,"cases":[],"complete":False,"errors":[],"budget_stop":None,"runtime_admitted":False,"optimiser_updates":0,"teacher_labels":0}
    try:
        with zipfile.ZipFile(D/"traces.zip","w",compression=zipfile.ZIP_STORED) as archive:
            for i,case in enumerate(selected):
                for enabled in (False,True):
                    arm = "candidate_refinement" if enabled else "shadow_only"
                    run = make_run(case["family"],case["seed"],case["pattern"],enabled,admission,budget)
                    while not run.finished: budget.charge("environment"); run.step()
                    payload = {"source_arm":arm,"scenario":run.scenario,"pattern":case["pattern"],"outcome":run.outcome(),"evaluation":run.evaluation(),
                               "frames":copy.deepcopy(run.records)+[run.frame()],"applied_machine_commands":False,
                               "candidate_forecasts_influence_actions":enabled,"applied_action_forecast_influences_action":False}
                    replay = make_run(case["family"],case["seed"],case["pattern"],enabled,admission,budget)
                    for frame in run.records:
                        budget.charge("replay"); replay.step()
                        if replay.records[-1] != frame: raise AssertionError("assistance controller/sensor/forecast/physics replay differs")
                    if replay.outcome() != run.outcome(): raise AssertionError("assistance replay outcome differs")
                    row = {"arm":arm,"family":case["family"],"seed":case["seed"],"pattern":case["pattern"],"outcome":payload["outcome"],
                        "evaluation":payload["evaluation"],"changed_actions":run.actor.changed,"neural_queries":run.feedback.calls,"model_rows":run.forecaster.rows,
                        "replay_neural_queries":replay.feedback.calls,"replay_model_rows":replay.forecaster.rows,
                        "cached_applied_predictions":run.forecaster.cache_hits,"replay_cached_applied_predictions":replay.forecaster.cache_hits,
                        **retain(archive,f"{i:02}-{arm}.json.gz",payload)}
                    report["cases"].append(row)
                    print("assistance",arm,case["family"],case["seed"],case["pattern"],row["evaluation"]["passed"],"changed",row["changed_actions"],flush=True)
        pairs = []
        for case in selected:
            a,b = [next(r for r in report["cases"] if r["arm"] == arm and (r["family"],r["seed"],r["pattern"]) == (case["family"],case["seed"],case["pattern"])) for arm in ("shadow_only","candidate_refinement")]
            both = a["evaluation"]["criterion"] == "delivery" and a["evaluation"]["passed"] and b["evaluation"]["passed"]
            pairs.append({"family":case["family"],"seed":case["seed"],"pattern":case["pattern"],"baseline_passed":a["evaluation"]["passed"],"assisted_passed":b["evaluation"]["passed"],
                          "both_deliveries":bool(both),"cycle_reduction_fraction":(a["outcome"]["cycle_s"]-b["outcome"]["cycle_s"])/a["outcome"]["cycle_s"] if both else None})
        changes = [r["cycle_reduction_fraction"] for r in pairs if r["both_deliveries"]]
        median = statistics.median(changes) if changes else None
        no_regression = all(not p["baseline_passed"] or p["assisted_passed"] for p in pairs)
        no_collision = not any(c["outcome"]["collision"] for c in report["cases"])
        report.update(pairs=pairs,median_paired_cycle_reduction=median,no_paired_criterion_regression=no_regression,
                      benefit_demonstrated=bool(no_regression and no_collision and median is not None and median >= .1),
                      complete=len(report["cases"]) == 2*len(selected),max_replay_error=0.)
        if sum(p.stat().st_size for p in D.rglob("*") if p.is_file()) > 96*1024**2: raise TimeoutError("artifact_cap")
    except TimeoutError as error: report["budget_stop"] = str(error)
    except Exception as error: report["errors"].append(type(error).__name__+": "+str(error))
    report["cost"] = budget.report(); seal(D,report); print("assistance result",report.get("benefit_demonstrated"),report["complete"],report["errors"],report["budget_stop"],report["cost"],flush=True)
    if not report["complete"] or report["errors"] or report["budget_stop"]: raise SystemExit(1)


if __name__ == "__main__": execute()
