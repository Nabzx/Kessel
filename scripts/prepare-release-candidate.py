"""Build a bounded repo-local static candidate. No tags, uploads or deployment."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import time
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def prepare(output):
    output = output.resolve()
    allowed = (ROOT / ".local").resolve()
    if not output.is_relative_to(allowed) or output == allowed:
        raise ValueError("candidate output must be a child of the repo's .local directory")
    spec = importlib.util.spec_from_file_location("package_static", ROOT / "scripts/package-static.py")
    package = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(package)
    paths = sorted(package.static_files(ROOT))
    size = sum(p.stat().st_size for p in paths)
    if size > 64 * 1024 * 1024:
        raise ValueError("candidate exceeds the 64 MiB uncompressed cap")
    selected = [p.relative_to(ROOT).as_posix() for p in paths]
    dirty = subprocess.check_output(["git", "diff", "HEAD", "--name-only", "--", *selected], cwd=ROOT, text=True)
    if dirty.strip():
        raise ValueError("commit static source changes before building a candidate")
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    manifest = {"kind": "kessel-local-static-candidate-v1", "source_commit": commit,
                "visual_acceptance": "open", "publication": "not_performed",
                "files": {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
                "uncompressed_bytes": size}
    output.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    archive = output / "kessel-static-candidate.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for p in paths:
            if time.monotonic() - started > 30:
                raise TimeoutError("candidate packaging exceeded its 30-second cap")
            info = zipfile.ZipInfo(p.relative_to(ROOT).as_posix(), (1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            z.writestr(info, p.read_bytes())
        z.writestr("release-manifest.json", json.dumps(manifest, indent=2) + "\n")
    with zipfile.ZipFile(archive) as z:
        assert set(z.namelist()) == set(manifest["files"]) | {"release-manifest.json"}
        for name, expected in manifest["files"].items():
            if hashlib.sha256(z.read(name)).hexdigest() != expected:
                raise ValueError("candidate archive differs: " + name)
    manifest.update(archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
                    archive_bytes=archive.stat().st_size, verified_files=len(paths))
    (output / "candidate.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"archive": str(archive.relative_to(ROOT)), "verified_files": len(paths),
                      "archive_bytes": manifest["archive_bytes"], "source_commit": commit,
                      "publication": manifest["publication"]}, indent=2))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, default=ROOT / ".local/release-candidate")
    prepare(p.parse_args().output)
