"""Bind experimental sensor display to immutable study and control receipts."""
import importlib.util
import json

from .harvest_admission import sha
from .runtime import ROOT, digest

D = ROOT/"docs/phase-11/sensor-forecast-v2-evidence"
MODEL = D/"sensor.pt"
LIVE = ROOT/"docs/phase-11/sensor-live-evidence"
SOURCES = tuple("training/kessel_lab/"+name+".py" for name in ("sensor_runtime","sensor_runtime_gate","sensor_runtime_check"))


def runtime_hash(): return digest({name:sha((ROOT/name).read_bytes()) for name in SOURCES})


def load_sensor_receipt():
    spec = importlib.util.spec_from_file_location("sensor_check",ROOT/"scripts/verify-sensor-forecast.py")
    verifier = importlib.util.module_from_spec(spec); spec.loader.exec_module(verifier); verifier.verify()
    raw = (D/"report.json").read_bytes(); r = json.loads(raw)
    # This wrapper is deliberately for the retained failed predictor. A future
    # qualified model requires its own review, protocol and implementation.
    if r["gate_passed"]: raise ValueError("experimental wrapper requires its declared failed-gate receipt")
    return {"gate_passed":False,"threshold":r["calibration"]["threshold"],"supported_families":[],
            "report_sha256":sha(raw),"checkpoint_sha256":sha(MODEL.read_bytes()),"source_kind":"recorded_synthetic"}


def verify_sensor_runtime():
    manifest = json.loads((LIVE/"files.json").read_text())
    for name,expected in manifest.items():
        if sha((ROOT/name).read_bytes()) != expected: raise ValueError("sensor live receipt artifact changed")
    raw = (LIVE/"report.json").read_bytes(); r = json.loads(raw)
    if not r["complete"] or r["errors"] or r["budget_stop"] or len(r["cases"]) != 38:
        raise ValueError("complete sensor wrapper control equivalence required")
    if not all(c["equivalent_to_frozen_control"] and c["evaluation"]["passed"] for c in r["cases"]):
        raise ValueError("sensor wrapper changed qualified control")
    for name,expected in r["plan"]["files"].items():
        if sha((ROOT/name).read_bytes()) != expected: raise ValueError("sensor wrapper source changed: "+name)
    if r["sensor_model_gate_passed"] or r["model_assisted_actions"] != 0: raise ValueError("experimental sensor model cannot qualify or assist control")
    return sha(raw)
