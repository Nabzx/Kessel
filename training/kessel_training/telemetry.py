"""Append-only, hash-chained events written by actual training transactions."""

import hashlib
import json
from pathlib import Path

from .contracts import canonical_json


def scan(path):
    rows=[];previous=None
    with Path(path).open() as stream:
        for line in stream:
            row=json.loads(line, parse_constant=lambda v: (_ for _ in ()).throw(ValueError(v)))
            digest=row.pop("sha256")
            if row["previous_sha256"] != previous or row["sequence"] != len(rows):
                raise ValueError("telemetry chain order differs")
            if hashlib.sha256(canonical_json(row).encode()).hexdigest() != digest:
                raise ValueError("telemetry content hash differs")
            row["sha256"]=digest;rows.append(row);previous=digest
    if not rows or rows[0]["kind"] != "header":raise ValueError("missing telemetry header")
    return rows


class EventLog:
    def __init__(self, path, source, configuration_sha256, counters):
        self.path=Path(path);self.sequence=0;self.previous=None
        if self.path.exists():
            rows=scan(path);header=rows[0]["payload"]
            if header["source"] != source or header["configuration_sha256"] != configuration_sha256:
                raise ValueError("telemetry belongs to another source/configuration")
            if rows[-1]["payload"]["counters"] != counters:
                raise ValueError("telemetry and resumed checkpoint counters differ; choose a new output")
            self.sequence=len(rows);self.previous=rows[-1]["sha256"]
            self.append("resume", {"counters":counters})
        else:
            self.path.touch(exist_ok=False)
            self.append("header", {"schema_version":"1.0", "source":source,
                "configuration_sha256":configuration_sha256,"counters":counters})

    def append(self, kind, payload):
        row={"sequence":self.sequence,"previous_sha256":self.previous,"kind":kind,"payload":payload}
        digest=hashlib.sha256(canonical_json(row).encode()).hexdigest();row["sha256"]=digest
        with self.path.open("a") as stream:stream.write(canonical_json(row)+"\n")
        self.sequence+=1;self.previous=digest

    def summary(self):
        rows=scan(self.path)
        return {"file":self.path.name,"records":len(rows),"last_event_sha256":rows[-1]["sha256"],
            "file_sha256":hashlib.sha256(self.path.read_bytes()).hexdigest(),
            "final_counters":rows[-1]["payload"]["counters"]}
