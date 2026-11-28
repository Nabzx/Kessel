"""Require the current live implementation's own equivalence receipt before serving."""
import hashlib
import json

from .runtime import ROOT


def verify_runtime_receipt():
    directory = ROOT/"docs/phase-11/harvest-live-evidence"
    manifest = json.loads((directory/"files.json").read_text())
    for name,digest in manifest.items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest() != digest: raise ValueError("live receipt artifact changed")
    raw = (directory/"report.json").read_bytes(); report = json.loads(raw)
    if not report["complete"] or report["errors"] or report["budget_stop"] or len(report["cases"]) != 38:
        raise ValueError("complete live equivalence receipt required")
    if any(report[k] != 0 for k in ("max_state_error","max_action_error","max_observation_error")) or not all(c["equivalent_to_frozen_control"] and c["evaluation"]["passed"] for c in report["cases"]):
        raise ValueError("live control differs from qualified execution")
    for name,digest in report["plan"]["files"].items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest() != digest: raise ValueError("live implementation changed: "+name)
    return hashlib.sha256(raw).hexdigest()
