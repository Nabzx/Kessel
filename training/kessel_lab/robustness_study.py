"""ADR-0074 bounded rehearsal, neural refit and full-family practice comparison."""
import copy
from collections import Counter
import io
import zipfile

import numpy as np
import torch
from torch.nn import functional as F

from kessel_training.phase_memory import features
from kessel_training.policy import configure_cpu
from kessel_training.wm_state import pack
from .robust_task import NeuralCandidate, RetryActor, TaskReference
from .runtime import ROOT, FAMILIES, checkpoint, environment
from .study_tools import Budget, begin, encode, retain, seal, sha, write

D = ROOT/"docs/phase-11/robustness-repair-evidence"


def rollout(family,seed,actor,budget,teacher=False):
    env,scenario = environment(family,seed); records = []; residual = 0.
    while True:
        budget.charge("environment")
        if teacher: budget.charge("teacher")
        obs = env.observe(); action = actor.act(obs)
        record = {"t_s":float(env.elapsed[0]),"state":pack(env)[0].tolist(),"phase":int(actor.memory.phase[0]),
                  "observation":{k:v[0].tolist() for k,v in obs.items()},"action":action[0].tolist(),
                  "supervision":copy.deepcopy(getattr(actor,"last",None)),"wheel_angles_rad":env.wheel_angles[0].tolist()}
        _,reward,term,trunc,info = env.step(action)
        record.update(next_state=pack(env)[0].tolist(),reward=float(reward[0]),
                      transfer={k:float(info["transfer"][k][0]) for k in ("loaded_kg","delivered_kg","spilled_kg")})
        records.append(record)
        residual = max(residual,abs(float(env.pile.mass()[0]+env.payload[0]+env.delivered[0]+env.spilled[0]-env.pile.initial_mass[0])))
        if residual > 1e-7: raise AssertionError("material ledger differs")
        if (term|trunc)[0]: break
    reason = str(env.reason[0])
    outcome = {"reason":reason,"full_success":reason == "success","collision":reason.startswith(("tunnel","obstacle")),
               "decisions":len(records),"initial_payload_kg":0.,"delivered_kg":float(env.delivered[0]),
               "peak_load_kg":float(env.peak_load[0]),"carried_kg":float(env.payload[0]),"spilled_kg":float(env.spilled[0]),
               "cycle_s":float(env.elapsed[0]),"max_mass_residual_kg":residual}
    final = {"t_s":float(env.elapsed[0]),"state":pack(env)[0].tolist(),"phase":int(actor.memory.phase[0]),
             "wheel_angles_rad":env.wheel_angles[0].tolist()}
    return {"scenario":scenario,"outcome":outcome,"frames":records+[final],"applied_machine_commands":False}


def rank(cases): return (sum(c["outcome"]["full_success"] for c in cases),-sum(c["outcome"]["collision"] for c in cases))


def train_actor(policy,timeout,rows,budget):
    configure_cpu(policy,threads=1); actor,initial_sha = checkpoint("phase_memory-"+str(policy))
    x = torch.as_tensor(np.asarray([r[0] for r in rows]),dtype=torch.float32)
    phase = torch.as_tensor([r[1] for r in rows]); y = torch.as_tensor([r[2] for r in rows],dtype=torch.float32)
    counts = torch.bincount(phase,minlength=5); sampling = 1/counts[phase].float(); sampling /= sampling.sum()
    optimiser = torch.optim.Adam(actor.parameters(),lr=.0003); generator = torch.Generator().manual_seed(policy); losses = []
    actor.train()
    for _ in range(1000):
        budget.charge("updates"); ids = torch.multinomial(sampling,512,replacement=True,generator=generator)
        loss = F.mse_loss(actor(x[ids],phase[ids]),y[ids])
        if not torch.isfinite(loss): raise FloatingPointError("nonfinite imitation loss")
        optimiser.zero_grad(); loss.backward(); torch.nn.utils.clip_grad_norm_(actor.parameters(),1.,error_if_nonfinite=True); optimiser.step()
        losses.append(float(loss.detach()))
    actor.eval(); payload = {"kind":"robustness-rehearsal-v1","seed":policy,"initial_checkpoint_sha256":initial_sha,
        "actor":actor.state_dict(),"fill_timeout_s":timeout,"updates":1000,"losses":losses,
        "training_rows_sha256":sha(encode(rows)),"phase_counts":counts.tolist()}
    buffer = io.BytesIO(); torch.save(payload,buffer); raw = buffer.getvalue()
    path = D/f"actor-{policy}.pt"; path.write_bytes(raw)
    return actor,{"seed":policy,"path":path.name,"sha256":sha(raw),"initial_checkpoint_sha256":initial_sha,
                  "updates":1000,"training_rows_sha256":payload["training_rows_sha256"],"phase_counts":counts.tolist(),
                  "initial_loss":losses[0],"final_loss":losses[-1]}


def execute():
    configure_cpu(7,threads=1); budget = Budget(600,environment=100000,teacher=30000,updates=3000,replay=25000)
    names = [str(p.relative_to(ROOT)) for p in (ROOT/"training/kessel_training").glob("*.py")]
    names += ["training/kessel_lab/"+n+".py" for n in ("robust_task","robustness_study","runtime","range_supervisor")]
    plan = begin(D,"docs/adr/0074-bounded-robustness-repair.md",names,{"kind":"bounded-robustness-repair-v1",
        "training_bases":[19010,19011],"validation_bases":[19012],"evaluation_bases":[19013],"families":list(FAMILIES),
        "policy_seeds":[7,19,41],"fill_variants_s":[6,12],"updates_per_actor":1000,"trace_cap_bytes":64*1024**2,
        "role":"consumed practice study; no fresh qualification","runtime_admitted":False})
    report = {"plan":plan,"cases":[],"models":[],"complete":False,"errors":[],"budget_stop":None,"runtime_admitted":False}
    try:
        with zipfile.ZipFile(D/"traces.zip","w",compression=zipfile.ZIP_STORED) as archive:
            training = {}
            def record(stage,source,payload):
                if (D/"traces.zip").stat().st_size >= plan["trace_cap_bytes"]: raise TimeoutError("trace_archive_cap")
                name = f"{len(report['cases']):03}-{stage}.json.gz"
                row = {"stage":stage,"source":source,"family":payload["scenario"]["family"],"seed":payload["scenario"]["seed"],
                       "outcome":payload["outcome"],**retain(archive,name,payload)}
                report["cases"].append(row); return row
            for timeout in plan["fill_variants_s"]:
                training[timeout] = []
                for seed in plan["training_bases"]:
                    for family in FAMILIES:
                        payload = rollout(family,seed,TaskReference(timeout),budget,teacher=True)
                        record("rehearsal",f"task_reference-{timeout}",payload); training[timeout].append(payload)
                print("reference rehearsal",timeout,rank(training[timeout]),flush=True)
            # Success count alone selects the declared reference variant; tie favours 12.
            timeout = max(plan["fill_variants_s"],key=lambda t:(rank(training[t])[0],t))
            report["selected_fill_timeout_s"] = timeout
            rows = []
            for episode in training[timeout]:
                for frame in episode["frames"][:-1]:
                    obs = {k:np.asarray([v]) for k,v in frame["observation"].items()}
                    rows.append((features(obs)[0].tolist(),frame["phase"],frame["action"]))
            report["training_rows"] = len(rows); report["training_rows_sha256"] = sha(encode(rows))
            trained = {}; choices = {}
            for policy in plan["policy_seeds"]:
                actor,metadata = train_actor(policy,timeout,rows,budget); report["models"].append(metadata); trained[policy] = actor
                validation = {}
                for smooth in (False,True):
                    validation[smooth] = []
                    for family in FAMILIES:
                        wrapper = NeuralCandidate(RetryActor(actor,timeout,smooth))
                        payload = rollout(family,19012,wrapper,budget)
                        record("validation",f"candidate-{policy}-smooth-{int(smooth)}",payload); validation[smooth].append(payload)
                    print("validation",policy,"smooth",smooth,rank(validation[smooth]),flush=True)
                choices[policy] = max((False,True),key=lambda s:(*rank(validation[s]),not s))
            report["selected_smoothing"] = {str(k):v for k,v in choices.items()}
            for policy in plan["policy_seeds"]:
                for method in ("original","candidate"):
                    for family in FAMILIES:
                        actor = checkpoint("phase_memory-"+str(policy))[0] if method == "original" else NeuralCandidate(RetryActor(trained[policy],timeout,choices[policy]))
                        payload = rollout(family,19013,actor,budget)
                        if method == "candidate":
                            env,_ = environment(family,19013)
                            for frame in payload["frames"][:-1]:
                                budget.charge("replay"); env.step([frame["action"]])
                                if pack(env)[0].tolist() != frame["next_state"]: raise AssertionError("candidate physics replay differs")
                        record("evaluation",f"{method}-{policy}",payload)
                    print("evaluation",policy,method,rank([c for c in report["cases"] if c["stage"] == "evaluation" and c["source"] == f"{method}-{policy}"]),flush=True)
        report["complete"] = len(report["cases"]) == 208 and len(report["models"]) == 3
        summary = []
        for family in FAMILIES:
            selected = [c for c in report["cases"] if c["stage"] == "evaluation" and c["family"] == family]
            summary.append({"family":family,**{method:{"successes":sum(c["outcome"]["full_success"] for c in selected if c["source"].startswith(method)),
                "collisions":sum(c["outcome"]["collision"] for c in selected if c["source"].startswith(method)),
                "reasons":dict(Counter(c["outcome"]["reason"] for c in selected if c["source"].startswith(method)))} for method in ("original","candidate")}})
        report["summary"] = summary; report["max_replay_state_error"] = 0.
    except TimeoutError as error: report["budget_stop"] = str(error)
    except Exception as error: report["errors"].append(type(error).__name__+": "+str(error))
    report["cost"] = budget.report(); seal(D,report)
    print("robustness complete",report["complete"],report["errors"],report["budget_stop"],report["cost"],flush=True)
    if not report["complete"] or report["errors"] or report["budget_stop"]: raise SystemExit(1)


if __name__ == "__main__": execute()
