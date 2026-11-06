#!/usr/bin/env python3
"""Verify frozen protocols, split isolation, model identities and sample accounting."""

import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]/"docs/phase-11"


def read(path):
    raw = gzip.decompress(path.read_bytes()).decode() if path.suffix == ".gz" else path.read_text()
    return json.loads(raw, parse_constant=lambda v: (_ for _ in ()).throw(ValueError(v)))


def verify_study(root, control_policy_hashes=None):
    root = root.resolve();index=read(root/"files.json")
    actual = {str(p.relative_to(root)) for p in root.rglob("*") if p.is_file() and p.name != "files.json"}
    if actual != {e["path"] for e in index["files"]}:raise ValueError("evidence file inventory differs")
    for entry in index["files"]:
        path=(root/entry["path"]).resolve()
        if not path.is_relative_to(root) or path.stat().st_size != entry["bytes"] or hashlib.sha256(path.read_bytes()).hexdigest() != entry["sha256"]:
            raise ValueError("evidence file hash differs")
    manifest, plan, completed=(read(root/n) for n in ("manifest.json", "plan.json", "completed.json"))
    canonical=json.dumps(plan, sort_keys=True, separators=(",", ":"), allow_nan=False)
    if hashlib.sha256(canonical.encode()).hexdigest() != manifest["plan_sha256"]:raise ValueError("plan hash differs")
    if manifest["source"] != completed["source"] or manifest["source"]["training_dirty"]:raise ValueError("unfrozen or mixed source")
    datasets=read(root/"datasets.json")["manifests"]
    seeds,piles=set(),set()
    for data in datasets.values():
        if data["transitions"] != sum(e["stop"]-e["start"] for e in data["episodes"]):raise ValueError("dataset row count differs")
        local_seeds={e["seed"] for e in data["episodes"]};local_piles={e["initial_pile_sha256"] for e in data["episodes"]}
        if seeds & local_seeds or piles & local_piles:raise ValueError("partition leakage")
        seeds |= local_seeds;piles |= local_piles
    for path in list((root/"models").glob("*.pt"))+list((root/"policies").glob("*.pt")):
        if hashlib.sha256(path.read_bytes()).hexdigest() != path.with_suffix(".pt.sha256").read_text().strip():raise ValueError("executable weight sidecar differs")
    policies={hashlib.sha256(p.read_bytes()).hexdigest() for p in (root/"policies").glob("*.pt")}
    known_policies=policies | (control_policy_hashes or set())
    comparison=read(root/"policy-comparison.json.gz");runs=comparison["runs"]
    for run in runs:
        if run["source"] != manifest["source"]:raise ValueError("training source differs")
        if run["policy_reference_steps"] != run["counters"]["environment_steps"]:raise ValueError("policy steps differ")
        if run["policy_reference_steps"]+run["offline_reference_steps_charged"] != run["total_reference_steps_charged"] or run["total_reference_steps_charged"] != 40960:
            raise ValueError("unequal charged reference budget")
        if len(run["learning_curve"]) != run["counters"]["rollouts"] or len(run["episodes"]) != run["counters"]["completed_episodes"]:raise ValueError("missing curve or episodes")
    step_key="additional_policy_reference_transitions" if "additional_policy_reference_transitions" in completed else "policy_reference_transitions"
    if sum(r["policy_reference_steps"] for r in runs) != completed[step_key]:raise ValueError("total policy accounting differs")
    for key,counter in (("accepted_imagined_transitions","imagined_transitions"),("auxiliary_critic_updates","auxiliary_updates")):
        if sum(r["counters"].get(counter,0) for r in runs) != completed[key]:raise ValueError("imagined accounting differs")
    scenes={}
    for row in comparison["test_comparisons"]:
        e=row["evaluation"];key=e["family"];ids=[c["scenario_sha256"] for c in e["cases"]]
        if key in scenes and scenes[key] != ids:raise ValueError("controllers saw different scenes")
        scenes[key]=ids
        if e["summary"]["successes"] != sum(c["reason"] == "success" for c in e["cases"]):raise ValueError("success count differs")
        if e["controller_kind"] != "reference" and e["identity"]["checkpoint_sha256"] not in known_policies:raise ValueError("evaluation policy missing")
    exports=read(root/"predictions.json.gz")
    for bundle in exports.values():
        for example in bundle["examples"]:
            for row in example["predictions"]:
                if row["prediction"] is None:
                    if row["residual"] is not None or row["missing_reason"] is None:raise ValueError("invented missing residual")
                    continue
                p,r=row["prediction"],row["reference"]
                delta=[a-b for a,b in zip(p["state"],r["state"])][:79];delta[2]=(delta[2]+3.141592653589793)%(2*3.141592653589793)-3.141592653589793
                if any(abs(a-b)>1e-10 for a,b in zip(delta,row["residual"]["state"])) or abs(p["cumulative_reward"]-r["cumulative_reward"]-row["residual"]["cumulative_reward"])>1e-10:raise ValueError("residual differs")
    return {"files":len(index["files"]),"runs":len(runs),"policy_hashes":policies,"seeds":seeds,"piles":piles}


def verify(root=ROOT):
    raw=verify_study(root/"world-model-evidence")
    follow=verify_study(root/"world-model-filter-evidence", raw["policy_hashes"])
    if raw["seeds"] & follow["seeds"] or raw["piles"] & follow["piles"]:raise ValueError("follow-up held-out data reuses original data")
    return {"files":raw["files"]+follow["files"],"policy_training_runs":raw["runs"]+follow["runs"]}


if __name__ == "__main__":print(json.dumps(verify()))
