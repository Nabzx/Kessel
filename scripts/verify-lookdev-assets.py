"""Verify the committed study assets against their recorded source hashes."""

import argparse
import hashlib
import json
import math
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parents[1]
STUDY = ROOT / "docs/phase-11/lookdev"


def check_file(path, expected_hash, expected_bytes=None):
    raw = path.read_bytes()
    if expected_bytes is not None and len(raw) != expected_bytes:
        raise ValueError(f"unexpected size: {path.name}")
    if hashlib.sha256(raw).hexdigest() != expected_hash:
        raise ValueError(f"SHA-256 mismatch: {path.name}")
    return raw


def verify(retained=False):
    manifest = json.loads((STUDY / "manifest.json").read_text())
    count = size = 0
    for material in manifest["materials"]:
        if material["licence"] != "CC0-1.0" or not material.get("creator"):
            raise ValueError("material source licence/creator missing")
        if {entry["role"] for entry in material["maps"]} != {"Diffuse", "nor_gl", "AO", "Rough"}:
            raise ValueError("incomplete PBR map set")
        for entry in material["maps"]:
            raw = check_file(STUDY / entry["path"], entry["sha256"], entry["bytes"])
            if hashlib.md5(raw).hexdigest() != entry["source_md5"]:
                raise ValueError("provider MD5 mismatch")
            count += 1
            size += len(raw)
    scan = json.loads((STUDY / "assets/slovenia-tunnel.json").read_text())
    raw = check_file(STUDY / "assets/slovenia-tunnel.bin", scan["derived_sha256"], scan["bytes"])
    if len(raw) != scan["triangles"]*9*4 or any(not math.isfinite(x[0]) for x in struct.iter_unpack("<f",raw)):
        raise ValueError("invalid scan geometry")
    if scan["physical_units"] is not None or scan["crs"] is not None or not scan["reference_only"]:
        raise ValueError("reference must not imply calibrated survey geometry")
    if scan["licence"] != "CC-BY-4.0" or not scan["attribution"]:
        raise ValueError("scan credit missing")
    if retained:
        for entry in manifest["retained_assets"]:
            check_file(ROOT / entry["path"],entry["sha256"],entry["bytes"])
    print(f"PASS: {count} maps ({size} bytes), {scan['triangles']} credited reference triangles; retained snapshot checked: {retained}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--retained",action="store_true",help="also check unchanged retained assets at the audit date")
    verify(parser.parse_args().retained)
