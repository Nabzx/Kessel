"""Package the static presentation without training tools or private artefacts."""

import argparse
from pathlib import Path
import shutil

ASSET_SUFFIXES = {
    ".jpg", ".jpeg", ".png", ".webp", ".svg", ".woff2", ".bin", ".gltf",
    ".glb", ".hdr", ".exr", ".ktx2", ".txt", ".md", ".ico", ".mp4", ".json",
}


def static_files(source):
    for name in ("index.html", "LICENSE"):
        path = source / name
        if path.is_file() and not path.is_symlink():
            yield path
    for directory, suffixes in (("css", {".css"}), ("js", {".js", ".mjs"}),
                                ("data", {".json"}), ("assets", ASSET_SUFFIXES)):
        for path in sorted((source / directory).rglob("*")):
            relative = path.relative_to(source)
            if any(part.startswith(".") for part in relative.parts):
                continue
            if any(parent.is_symlink() for parent in path.parents if parent != source):
                continue
            vendored_runtime = (directory == "assets" and len(relative.parts) > 2
                                and relative.parts[1] == "vendor"
                                and path.suffix.lower() in {".js", ".mjs", ".wasm"})
            if path.is_file() and not path.is_symlink() and (path.suffix.lower() in suffixes or vendored_runtime):
                yield path


def package(source, output):
    source, output = source.resolve(), output.resolve()
    if not (source / "index.html").is_file():
        raise ValueError("source must contain index.html")
    if output == source or source in output.parents:
        raise ValueError("output must be outside the source repository")
    files = list(static_files(source))
    output.mkdir(parents=True, exist_ok=False)
    size = 0
    for path in files:
        target = output / path.relative_to(source)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
        size += path.stat().st_size
    return len(files), size


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    count, size = package(args.source, args.output)
    print(f"Packaged {count} static files ({size} bytes) into {args.output}")
