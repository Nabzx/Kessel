"""Bounded historical/raw/ZIP audit before any fresh stopping-policy query."""
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import zipfile

import numpy as np
import torch
from kessel_training.phase_memory import PhaseActor
from kessel_training.policy import configure_cpu
from kessel_training.wm_state import pack
from .runtime import ROOT, FAMILIES
from .harvest_scenarios import environment
from .harvest_contract import certificate
from .structured_data import fixture

SEEDS = tuple(range(207400,207432))
RARE_SEEDS = tuple(range(207450,207466))
GUARD_SEEDS = tuple(range(207470,207478))
ALL_SEEDS = SEEDS+RARE_SEEDS+GUARD_SEEDS
D = ROOT/"docs/phase-11/harvest-qualification-evidence"
OUTPUT = D/"reservation.json"
WORK = ROOT/".local/harvest-reservation-work"
SUFFIXES = (".json.gz",".jsonl",".json",".pt",".npz",".zip")
MAX_BYTES = 256*1024**2


def sha(raw): return hashlib.sha256(raw).hexdigest()


def inspect(value, seeds, fingerprints, first_cells):
    """Seed checks always run; f32 first-cell filtering is necessary for a hash match."""
    hits = []; stack = [("",value)]
    def check_arrays(rows):
        for row in rows:
            if float(np.float32(row[0])) not in first_cells: continue
            for dtype in ("<f8","<f4"):
                digest = sha(np.asarray(row,dtype=dtype).tobytes())
                if digest in fingerprints: hits.append({"kind":"pile","sha256":digest})
    def check_states(rows):
        for row in rows:
            if float(np.float32(row[15])) not in first_cells: continue
            check_arrays([row[15:79]])
            for dtype in ("<f8","<f4"):
                digest = sha(np.asarray(row,dtype=dtype).tobytes())
                if digest in fingerprints: hits.append({"kind":"state","sha256":digest})
    while stack:
        key,item = stack.pop()
        if isinstance(item,torch.Tensor): item = item.detach().cpu().numpy()
        if isinstance(item,np.ndarray):
            if "seed" in key.lower():
                hits.extend({"kind":"seed","value":int(v),"key":key} for v in np.unique(item) if v in seeds)
            if item.dtype.kind == "f" and item.ndim and item.shape[-1] == 102:
                rows = item.reshape(-1,102)
                selected = np.isin(rows[:,15].astype(np.float32),list(first_cells))
                check_states(rows[selected])
            if item.dtype.kind == "f" and item.ndim >= 2 and item.shape[-2:] == (8,8):
                rows = item.reshape(-1,64)
                selected = np.isin(rows[:,0].astype(np.float32),list(first_cells))
                check_arrays(rows[selected])
        elif isinstance(item,dict): stack.extend((str(k),v) for k,v in item.items())
        elif isinstance(item,(tuple,list)):
            if "seed" in key.lower() and all(isinstance(v,(int,float)) for v in item):
                hits.extend({"kind":"seed","value":int(v),"key":key} for v in item if v in seeds)
            elif key in ("state","states","initial_state","next_state") and len(item) == 102 and isinstance(item[15],(int,float)):
                # Conversion of all 102 values is unnecessary when the pile cannot match.
                if float(np.float32(item[15])) in first_cells: check_states([np.asarray(item)])
            elif len(item) == 8 and all(isinstance(r,list) and len(r) == 8 for r in item):
                if isinstance(item[0][0],(int,float)):
                    if float(np.float32(item[0][0])) in first_cells: check_arrays([np.asarray(item).reshape(64)])
                else: stack.extend((key,v) for v in item)
            elif item and isinstance(item[0],(dict,tuple,list,str)): stack.extend((key,v) for v in item)
        elif isinstance(item,(int,float)) and "seed" in key.lower() and item in seeds:
            hits.append({"kind":"seed","value":int(item),"key":key})
        elif isinstance(item,str):
            if item in fingerprints: hits.append({"kind":"fingerprint","sha256":item})
            if "seed" in key.lower() and item.isdigit() and int(item) in seeds:
                hits.append({"kind":"seed","value":int(item),"key":key})
    return hits


def worker():
    configure_cpu(7,threads=1); started = time.monotonic()
    rows = []; fingerprints = set(); first_cells = set()
    original_act,original_forward = PhaseActor.act,PhaseActor.forward
    def reject(*args,**kwargs): raise AssertionError("policy queried during reservation")
    PhaseActor.act = PhaseActor.forward = reject
    try:
        jobs = [(family,seed) for seed in SEEDS for family in FAMILIES]
        jobs += [("prepared_"+("collision" if seed < 207458 else "stuck"),seed) for seed in RARE_SEEDS]
        jobs += [("prepared_no_progress",seed) for seed in GUARD_SEEDS]
        for family,seed in jobs:
            if family in ("prepared_collision","prepared_stuck"):
                env = fixture(family[9:],seed); identity = {"seed":seed,"family":family}
            else: env,identity = environment(family,seed)
            state = pack(env)[0]
            row = {"seed":seed,"family":family,"scenario":identity,"certificate":certificate(state),"fingerprints":{}}
            first_cells.add(float(np.float32(state[15])))
            for dtype in ("<f8","<f4"):
                for kind,array in (("state",state),("pile",state[15:79])):
                    digest = sha(array.astype(dtype).tobytes()); fingerprints.add(digest)
                    row["fingerprints"][kind+dtype] = digest
            rows.append(row)
    finally: PhaseActor.act,PhaseActor.forward = original_act,original_forward
    inventory = {}; hits = []; errors = []
    def deadline():
        if time.monotonic()-started >= 235: raise TimeoutError("235-second worker deadline")
    def scan(raw,name,location):
        deadline()
        if len(raw) > MAX_BYTES: raise ValueError("raw input exceeds 256 MiB")
        digest = sha(raw)
        if digest in inventory:
            inventory[digest]["locations"].append(location); return
        inventory[digest] = {"format":next(s for s in SUFFIXES if name.endswith(s)),"locations":[location]}
        if name.endswith(".zip"):
            with zipfile.ZipFile(io.BytesIO(raw)) as z:
                for member in z.infolist():
                    deadline()
                    if member.filename.endswith(SUFFIXES):
                        if member.file_size > MAX_BYTES: raise ValueError("ZIP member exceeds 256 MiB")
                        scan(z.read(member),member.filename,location+":"+member.filename)
            return
        if name.endswith(".gz"):
            with gzip.GzipFile(fileobj=io.BytesIO(raw)) as stream: data = stream.read(MAX_BYTES+1)
        else: data = raw
        if len(data) > MAX_BYTES: raise ValueError("decoded input exceeds 256 MiB")
        if name.endswith((".pt",".npz")) and zipfile.is_zipfile(io.BytesIO(data)):
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                if sum(m.file_size for m in z.infolist()) > MAX_BYTES:
                    raise ValueError("decoded numerical container exceeds 256 MiB")
        if name.endswith(".pt"): value = torch.load(io.BytesIO(data),map_location="cpu",weights_only=True)
        elif name.endswith(".npz"):
            with np.load(io.BytesIO(data),allow_pickle=False) as a: value = {k:a[k] for k in a.files}
        elif name.endswith(".jsonl"): value = [json.loads(line) for line in data.splitlines() if line.strip()]
        else: value = json.loads(data)
        found = inspect(value,set(ALL_SEEDS),fingerprints,first_cells)
        if found: hits.append({"location":location,"hits":found})
    history = subprocess.check_output(["git","rev-list","--objects","--all","--","data","docs/phase-11","training"],cwd=ROOT,text=True)
    proc = subprocess.Popen(["git","cat-file","--batch"],cwd=ROOT,stdin=subprocess.PIPE,stdout=subprocess.PIPE)
    try:
        for line in history.splitlines():
            parts = line.split(" ",1)
            if len(parts) != 2 or not parts[1].endswith(SUFFIXES): continue
            deadline(); oid,name = parts
            proc.stdin.write((oid+"\n").encode()); proc.stdin.flush()
            header = proc.stdout.readline().decode().split()
            if len(header) != 3 or header[1] != "blob": raise ValueError("unreadable Git blob")
            size = int(header[2])
            if size > MAX_BYTES: raise ValueError("historical blob exceeds 256 MiB")
            raw = proc.stdout.read(size)
            if len(raw) != size or proc.stdout.read(1) != b"\n": raise ValueError("short Git blob read")
            try: scan(raw,name,"git:"+oid+":"+name)
            except (TimeoutError,MemoryError): raise
            except Exception as error: errors.append({"location":"git:"+oid+":"+name,"error":str(error)})
        for folder in ("data","docs/phase-11","training",".local"):
            for base,dirs,names in os.walk(ROOT/folder):
                dirs[:] = [d for d in dirs if d not in (".git",".venv","__pycache__") and Path(base)/d != WORK]
                for name in names:
                    path = Path(base)/name
                    if not name.endswith(SUFFIXES) or path == OUTPUT: continue
                    deadline()
                    try:
                        if path.stat().st_size > MAX_BYTES: raise ValueError("local input exceeds 256 MiB")
                        scan(path.read_bytes(),name,path.relative_to(ROOT).as_posix())
                    except (TimeoutError,MemoryError): raise
                    except Exception as error: errors.append({"location":path.relative_to(ROOT).as_posix(),"error":str(error)})
    finally:
        proc.stdin.close(); proc.stdout.close(); proc.wait(timeout=3)
    selected = {f:[r["seed"] for r in rows if r["family"] == f and r["certificate"]["supported"]][:8] for f in FAMILIES}
    if any(len(v) != 8 for v in selected.values()): errors.append({"error":"fewer than eight eligible initial cases in fixed screening cohort"})
    result = {"selected_by_family":selected,"kind":"harvest-fresh-reservation-v1","seeds":list(SEEDS),"rare_seeds":list(RARE_SEEDS),"guard_seeds":list(GUARD_SEEDS),"verified":not hits and not errors,
              "identities":rows,"first_cells_float32":sorted(first_cells),"history_listing_sha256":sha(history.encode()),
              "inventory":inventory,"hits":hits,"errors":errors,"new_policy_queries":0,"cpu_threads":1,
              "worker_wall_s":time.monotonic()-started,"worker_cap_s":235,
              "audit_commit":subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),
              "audit_files":{name:sha((ROOT/name).read_bytes()) for name in (
                  "training/kessel_lab/reserve_harvest.py","training/kessel_lab/runtime.py",
                  "training/kessel_training/environment.py","training/kessel_training/pile.py",
                  "training/kessel_training/wm_state.py","docs/adr/0084-frozen-harvest-and-forecast-qualification.md",
                  "training/kessel_lab/structured_data.py","training/kessel_lab/structured_model.py",
                  "training/kessel_lab/harvest_scenarios.py","training/kessel_lab/harvest_contract.py")},
              "scope":"all available Git versions including ZIPs, plus current repo data/docs/training/.local; excludes audit scratch, environments and Git internals; not unretained external experiments"}
    encoded = json.dumps(result,indent=2,allow_nan=False)+"\n"
    if len(encoded.encode()) > 16*1024**2: raise ValueError("certificate exceeds 16 MiB")
    OUTPUT.write_text(encoded)
    if not result["verified"]: raise ValueError("fresh reservation rejected")
    print("Audited",len(inventory),"unique raw/container/member blobs; zero hits/errors",flush=True)


def main():
    if OUTPUT.exists() or WORK.exists(): raise FileExistsError("reservation or scratch exists")
    D.mkdir(parents=True,exist_ok=True); WORK.mkdir(parents=True)
    started = time.monotonic(); env = dict(os.environ)
    env.update(OMP_NUM_THREADS="1",VECLIB_MAXIMUM_THREADS="1",TMPDIR=str(ROOT/".local/test-tmp"))
    try:
        result = subprocess.run([sys.executable,"-m","kessel_lab.reserve_harvest","--worker"],cwd=ROOT/"training",env=env,timeout=240)
        if result.returncode: raise RuntimeError("reservation worker failed")
        cert = json.loads(OUTPUT.read_text()); cert["audit_wall_s"] = time.monotonic()-started; cert["audit_cap_s"] = 240
        if cert["audit_wall_s"] > 240: raise TimeoutError("parent audit cap")
        OUTPUT.write_text(json.dumps(cert,indent=2)+"\n")
    except Exception as error:
        failure = json.loads(OUTPUT.read_text()) if OUTPUT.exists() else {}
        failure.update(verified=False,error=str(error),new_policy_queries=0)
        OUTPUT.write_text(json.dumps(failure,indent=2)+"\n"); raise


if __name__ == "__main__": worker() if "--worker" in sys.argv else main()
