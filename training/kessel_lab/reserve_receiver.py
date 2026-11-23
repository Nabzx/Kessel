"""Bounded repo-local archive audit for the frozen receiver qualification."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import zipfile

from kessel_training import reserve_scenarios as audit
from .runtime import ROOT

OUTPUT = ROOT / "docs/phase-11/receiver-evidence/reservation.json"
WORK = ROOT / ".local/receiver-reservation-work"
SEEDS = list(range(205800,205808))


def worker():
    audit.RANGES = {"receiver_test": (SEEDS[0],SEEDS[-1]+1)}
    WORK.mkdir(parents=True,exist_ok=True)
    original = WORK / "base.json"
    try:
        audit.reserve(ROOT,original)
    except ValueError:
        pass
    base=json.loads(original.read_text())
    fingerprints={v for row in base["identities"] for start in row["starts"].values()
                  for k,v in start.items() if k.endswith("sha256")}
    seen=set(base["archive_inventory"]);inventory=[];hits=[];errors=[]
    def inspect(path,name,raw):
        sha=hashlib.sha256(raw).hexdigest()
        inventory.append({"location":path,"sha256":sha})
        if sha in seen:return
        seen.add(sha)
        found=audit.inspect(raw,name,set(SEEDS),fingerprints)
        if found:hits.append({"location":path,"hits":found})
    # The old audit scans raw data/docs/training archives; extend it to .local.
    for p in sorted((ROOT/".local").rglob("*")):
        if not p.is_file() or WORK in p.parents or ".venv" in p.parts:continue
        if p.name.endswith((".json",".json.gz",".jsonl",".pt",".npz")):
            try:inspect(p.relative_to(ROOT).as_posix(),p.name,p.read_bytes())
            except Exception as error:errors.append({"location":str(p),"error":str(error)})
    for folder in ("docs/phase-11","training","data",".local"):
        for p in sorted((ROOT/folder).rglob("*.zip")):
            if ".venv" in p.parts or WORK in p.parents:continue
            try:
                with zipfile.ZipFile(p) as z:
                    for name in z.namelist():
                        if name.endswith((".json",".json.gz",".jsonl",".pt",".npz")):
                            inspect(p.relative_to(ROOT).as_posix()+":"+name,name,z.read(name))
            except Exception as error:errors.append({"location":str(p),"error":str(error)})
    result={"kind":"receiver-reservation-v1","seeds":SEEDS,
            "verified":base["reservation_verified"] and not hits and not errors,
            "base":base,"additional_inventory":inventory,"hits":hits,"errors":errors,
            "new_policy_queries":0,"cpu_threads":1,"scope":
            "available local Git refs/history and repo data/docs/training/.local raw archives and ZIP members; excludes this audit's scratch output and unretained external runs"}
    OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    OUTPUT.write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    if not result["verified"]:raise ValueError("fresh-case audit failed")
    print("Reserved",SEEDS[0],"-",SEEDS[-1],"across",base["unique_blobs"],
          "raw/history blobs and",len(inventory),"additional raw/ZIP entries",flush=True)


def main():
    if OUTPUT.exists() or WORK.exists():
        raise FileExistsError("reservation or audit workspace already exists")
    env=dict(os.environ)
    env.update(OMP_NUM_THREADS="1",VECLIB_MAXIMUM_THREADS="1",TMPDIR=str(ROOT/".local/test-tmp"))
    started=time.monotonic()
    try:
        result=subprocess.run([sys.executable,"-m","kessel_lab.reserve_receiver","--worker"],
                              cwd=ROOT/"training",env=env,timeout=180)
        if result.returncode:raise RuntimeError("receiver audit worker failed")
    except subprocess.TimeoutExpired:
        OUTPUT.write_text(json.dumps({"verified":False,"reason":"180-second audit cap","new_policy_queries":0})+"\n")
        raise
    print("Audit duration",round(time.monotonic()-started,2),"seconds",flush=True)


if __name__=="__main__":
    worker() if "--worker" in sys.argv else main()
