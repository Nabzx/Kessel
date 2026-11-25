"""ADR-0071: audit only the replacement base and bind the untouched prior cohort."""
import hashlib
import json
import os
import subprocess
import sys
import time
from . import reserve_bootstrap as audit
from .runtime import ROOT

D = ROOT/"docs/phase-11/bootstrap-qualification-evidence"
audit.SEEDS = (208708,)
audit.OUTPUT = D/"reservation-replacement.json"
audit.WORK = ROOT/".local/bootstrap-replacement-reservation-work"


def main():
    combined_path = D/"reservation-corrected.json"
    if audit.OUTPUT.exists() or audit.WORK.exists() or combined_path.exists(): raise FileExistsError("replacement audit exists")
    audit.WORK.mkdir(parents=True)
    env = dict(os.environ); env.update(OMP_NUM_THREADS="1",VECLIB_MAXIMUM_THREADS="1",TMPDIR=str(ROOT/".local/test-tmp"))
    started = time.monotonic()
    try:
        result = subprocess.run([sys.executable,"-m","kessel_lab.reserve_bootstrap_replacement","--worker"],cwd=ROOT/"training",env=env,timeout=180)
        if result.returncode: raise RuntimeError("replacement audit failed")
        replacement = json.loads(audit.OUTPUT.read_text())
        replacement.update(audit_wall_s=time.monotonic()-started,audit_cap_s=180)
        if replacement["audit_wall_s"] > 180 or not replacement["verified"]: raise ValueError("replacement audit cap or failure")
        audit.OUTPUT.write_text(json.dumps(replacement,indent=2)+"\n")
        original_path = D/"reservation.json"; original = json.loads(original_path.read_text())
        if not original["verified"] or original["seeds"] != list(range(208700,208708)): raise ValueError("prior certificate differs")
        files = {**original["audit_files"],**replacement["audit_files"]}
        for name in ("training/kessel_lab/reserve_bootstrap_replacement.py","docs/adr/0071-fresh-qualification-logging-erratum.md"):
            files[name] = hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
        combined = {"kind":"combined-bootstrap-fresh-reservation-v1","verified":True,
            "seeds":list(range(208701,208709)),"excluded_consumed_bases":[208700],
            "identities":[r for r in original["identities"] if r["seed"] != 208700]+replacement["identities"],
            "audits":[{"path":str(p.relative_to(ROOT)),"sha256":hashlib.sha256(p.read_bytes()).hexdigest()}
                      for p in (original_path,audit.OUTPUT)],
            "audit_files":files,"hits":[],"errors":[],"new_policy_queries":0,
            "scope":"208701-208707 from original pre-query audit; 208708 from separate full replacement audit; 208700 excluded as consumed"}
        combined_path.write_text(json.dumps(combined,indent=2)+"\n")
        print("Combined untouched seven bases with audited replacement; excludes consumed 208700",flush=True)
    except Exception as error:
        value = json.loads(audit.OUTPUT.read_text()) if audit.OUTPUT.exists() else {}
        value.update(verified=False,error=str(error),new_policy_queries=0)
        audit.OUTPUT.write_text(json.dumps(value,indent=2)+"\n"); raise


if __name__ == "__main__": audit.worker() if "--worker" in sys.argv else main()
