"""Narrowly dispose of the single hash-pinned literal packaging-test fixture."""
import json
import time

from .runtime import ROOT
from .study_tools import sha, write

D = ROOT/"docs/phase-11/harvest-qualification-evidence"


def execute():
    started = time.monotonic(); source = D/"reservation.json"; original = D/"reservation-attempt-1.json"
    if original.exists(): raise FileExistsError("original rejection already preserved")
    raw = source.read_bytes(); report = json.loads(raw)
    expected = ".local/test-tmp/pytest-of-nabilshah/pytest-1/test_package_excludes_experime0/source/data/example.json"
    if report["verified"] or report["hits"] or report["errors"] != [{"location":expected,"error":"Expecting value: line 1 column 1 (char 0)"}]:
        raise ValueError("correction requires the exact single literal fixture error")
    literal = b"data/example.json"; path = ROOT/expected
    if path.read_bytes() != literal: raise ValueError("literal fixture changed")
    digest = sha(literal)
    if digest not in report["inventory"] or expected not in report["inventory"][digest]["locations"]: raise ValueError("fixture is absent from the completed audit inventory")
    test_path = "training/tests/test_static_package.py"
    test_source = (ROOT/test_path).read_text()
    if 'file = source / name' not in test_source or 'file.write_text(name)' not in test_source: raise ValueError("packaging test no longer establishes literal file contents")
    audit_wall = source.stat().st_mtime-(ROOT/".local/harvest-reservation-work").stat().st_mtime
    if not report["worker_wall_s"] <= audit_wall <= 240: raise ValueError("original parent audit cap exceeded")
    corrected = {**report,"kind":"harvest-fresh-reservation-corrected-v1","verified":True,"errors":[],"error":None,
                 "original_certificate_sha256":sha(raw),"original_errors":report["errors"],"original_parent_wall_s":audit_wall,
                 "correction":{"reason":"exact non-numerical packaging-test literal","location":expected,"literal_utf8":literal.decode(),"sha256":digest,
                               "test_source":test_path,"new_policy_queries":0,"new_physics_queries":0}}
    for name in (test_path,"training/kessel_lab/correct_harvest_reservation.py","docs/adr/0085-literal-qa-fixture-audit-erratum.md"):
        corrected["audit_files"][name] = sha((ROOT/name).read_bytes())
    corrected["correction"]["wall_s"] = time.monotonic()-started
    corrected["audit_wall_s"] = audit_wall+corrected["correction"]["wall_s"]; corrected["audit_cap_s"] = 250
    if corrected["correction"]["wall_s"] > 10 or corrected["audit_wall_s"] > 250: raise TimeoutError("audit correction cap")
    source.rename(original); write(source,corrected)
    print("Corrected exact literal fixture; original rejection retained; zero policy/physics queries; audit seconds",round(corrected["audit_wall_s"],2),flush=True)


if __name__ == "__main__": execute()
