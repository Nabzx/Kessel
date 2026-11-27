"""Small bounded-study utilities. No sockets, subprocess workers or teacher calls."""
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import time
import zipfile

from .runtime import ROOT


def sha(raw): return hashlib.sha256(raw).hexdigest()
def encode(value): return json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
def write(path,value): Path(path).write_bytes(encode(value)+b"\n")


class Budget:
    def __init__(self,wall_s,**limits):
        self.started = time.monotonic(); self.wall_s = wall_s
        self.limits = limits; self.counts = dict.fromkeys(limits,0)
    def check(self):
        if self.elapsed >= self.wall_s: raise TimeoutError("wall_cap")
    def charge(self,key,count=1):
        self.check()
        if self.counts[key]+count > self.limits[key]: raise TimeoutError(key+"_cap")
        self.counts[key] += count
    @property
    def elapsed(self): return time.monotonic()-self.started
    def report(self): return {"wall_s":self.elapsed,"wall_cap_s":self.wall_s,"counts":self.counts,"limits":self.limits}


def begin(directory,protocol,names,plan):
    directory.mkdir(parents=True,exist_ok=False)
    names = set(names)|{"training/kessel_lab/study_tools.py",protocol}
    files = {name:sha((ROOT/name).read_bytes()) for name in sorted(names)}
    plan = {**plan,"protocol":protocol,"files":files,"cpu_threads":1,
            "commit":subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()}
    write(directory/"plan.json",plan)
    with zipfile.ZipFile(directory/"source.zip","w",compression=zipfile.ZIP_DEFLATED) as archive:
        for name in files: archive.write(ROOT/name,name)
    return plan


def retain(archive,name,value):
    raw = gzip.compress(encode(value),mtime=0); archive.writestr(name,raw)
    return {"trace":name,"sha256":sha(raw)}


def seal(directory,report):
    write(directory/"report.json",report)
    files = {str(p.relative_to(ROOT)):sha(p.read_bytes()) for p in sorted(directory.rglob("*")) if p.is_file() and p.name != "files.json"}
    write(directory/"files.json",files)
