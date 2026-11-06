"""Restore the exact approved CC0 maps from static public download URLs."""

import argparse
import hashlib
import json
from pathlib import Path
import urllib.request


def restore(output):
    root = Path(__file__).resolve().parents[1]
    manifest = json.loads((root / "docs/phase-11/lookdev/manifest.json").read_text())
    output.mkdir(parents=True,exist_ok=True)
    for material in manifest["materials"]:
        for entry in material["maps"]:
            path = output / entry["file"]
            if path.exists():
                raw = path.read_bytes()
            else:
                request = urllib.request.Request(entry["source_url"],headers={"User-Agent":"Kessel asset research; source audit"})
                with urllib.request.urlopen(request,timeout=45) as response:
                    raw = response.read(entry["bytes"]+1)
            if len(raw) != entry["bytes"] or hashlib.sha256(raw).hexdigest() != entry["sha256"]:
                raise ValueError(f"source changed or invalid download: {entry['file']}")
            if not path.exists():
                path.write_bytes(raw)
            print("Verified",entry["file"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,required=True)
    restore(parser.parse_args().output)
