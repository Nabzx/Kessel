#!/usr/bin/env python3
"""Supplement the pre-query audit with historical ZIP versions; no policy calls."""
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import time
import zipfile

ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/"training"))
from kessel_training.reserve_scenarios import inspect
D=ROOT/"docs/phase-11/receiver-evidence"
cert=json.loads((D/"reservation.json").read_text())
seeds=set(cert["seeds"])
fingerprints={v for row in cert["base"]["identities"] for start in row["starts"].values()
              for k,v in start.items() if k.endswith("sha256")}
seen=set(cert["base"]["archive_inventory"])|{r["sha256"] for r in cert["additional_inventory"]}
started=time.monotonic()
listing=subprocess.check_output(["git","rev-list","--objects","--all","--","data","docs/phase-11","training"],cwd=ROOT,text=True)
inventory=[];hits=[];skipped=[];new_members=0
for line in listing.splitlines():
    parts=line.split(" ",1)
    if len(parts)!=2 or not parts[1].endswith(".zip"):continue
    oid,name=parts
    # These are the outputs of the current test, not previous consumption.
    if name.startswith("docs/phase-11/receiver-evidence/qualification-"):
        skipped.append({"oid":oid,"path":name,"reason":"current qualification output"});continue
    if time.monotonic()-started>15:raise TimeoutError("historical ZIP supplement exceeded 15 seconds")
    raw=subprocess.check_output(["git","cat-file","blob",oid],cwd=ROOT,timeout=max(.1,15-(time.monotonic()-started)))
    inventory.append({"oid":oid,"path":name,"sha256":hashlib.sha256(raw).hexdigest()})
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        for member in z.namelist():
            if not member.endswith((".json",".json.gz",".jsonl",".pt",".npz")):continue
            if time.monotonic()-started>15:raise TimeoutError("historical ZIP supplement exceeded 15 seconds")
            data=z.read(member);sha=hashlib.sha256(data).hexdigest()
            if sha in seen:continue
            seen.add(sha);new_members+=1
            found=inspect(data,member,seeds,fingerprints)
            if found:hits.append({"path":name+":"+member,"oid":oid,"hits":found})
result={"verified":not hits,"role":"supplemental historical-ZIP check after outcome freeze; no new policy queries",
        "reservation_sha256":hashlib.sha256((D/"reservation.json").read_bytes()).hexdigest(),
        "inventory":inventory,"excluded_current_outputs":skipped,"new_member_blobs":new_members,
        "hits":hits,"wall_s":time.monotonic()-started,"cap_s":15,"new_policy_queries":0}
(D/"zip-history.json").write_text(json.dumps(result,indent=2)+"\n")
if hits:raise ValueError("historical consumption invalidates fresh-case interpretation")
print("Historical ZIP check passed:",len(inventory),"versions;",new_members,"additional member blobs;",round(result["wall_s"],2),"seconds")
