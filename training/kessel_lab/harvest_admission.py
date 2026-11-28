"""Verify frozen evidence before admitting the isolated synthetic runtime."""
import hashlib
import importlib.util
import json

import numpy as np
import torch

from .runtime import ROOT

D = ROOT/"docs/phase-11/harvest-qualification-evidence"
FEEDBACK = ROOT/"docs/phase-11/linear-feedback-evidence/feedback.pt"
FORECAST = ROOT/"docs/phase-11/structured-dynamics-evidence/structured.pt"


def sha(raw): return hashlib.sha256(raw).hexdigest()


def load_admission():
    spec = importlib.util.spec_from_file_location("harvest_evidence_check",ROOT/"scripts/verify-harvest-qualification.py")
    check = importlib.util.module_from_spec(spec); spec.loader.exec_module(check); check.verify()
    raw = (D/"fresh/report.json").read_bytes(); report = json.loads(raw)
    decision = json.loads((D/"start-refusal-acceptance.json").read_text())
    if not report["supported_envelope_gate"] or not report["start_guard_qualified"] or not report["forecast"]["gate_passed"]:
        raise ValueError("complete supported task, start-hold and forecast qualification required")
    if decision["status"] != "accepted" or decision["qualification_report_sha256"] != sha(raw):
        raise ValueError("matching explicit start-hold acceptance required")
    environment = json.loads((D/"execution-environment.json").read_text())
    if environment["distributions"]["numpy"] != np.__version__ or environment["distributions"]["torch"].split("+")[0] != str(torch.__version__).split("+")[0]:
        raise ValueError("numeric library releases differ from qualification")
    for path,key in ((FEEDBACK,"feedback_sha256"),(FORECAST,"forecast_sha256")):
        if sha(path.read_bytes()) != report["plan"][key]: raise ValueError("qualified weights differ")
    return {"qualification_sha256":sha(raw),"feedback_sha256":report["plan"]["feedback_sha256"],
            "forecast_sha256":report["plan"]["forecast_sha256"],"acceptance_sha256":sha((D/"start-refusal-acceptance.json").read_bytes()),
            "forecast_gate":report["forecast"]["calibration_gate"],"scope":"conditional synthetic qualification; no field admission"}
