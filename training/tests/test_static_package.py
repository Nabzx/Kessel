import importlib.util
import json
from pathlib import Path
import re

import pytest

spec = importlib.util.spec_from_file_location("static_package", Path(__file__).parents[2] / "scripts/package-static.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_package_excludes_experiment_files_and_preserves_credits(tmp_path):
    source = tmp_path / "source"
    paths = ["index.html", "LICENSE", "js/app.js", "assets/model.bin", "assets/vendor/engine.js",
             "assets/README.md", "assets/.private/image.png", "data/example.json",
             "data/generator.py", "training/model.bin", ".venv/tool.py", ".git/config"]
    for name in paths:
        file = source / name
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(name)
    (source / "assets/leak.bin").symlink_to(source / "training/model.bin")
    output = tmp_path / "public"
    count, _ = module.package(source, output)
    assert count == 7
    assert sorted(str(p.relative_to(output)) for p in output.rglob("*") if p.is_file()) == [
        "LICENSE", "assets/README.md", "assets/model.bin", "assets/vendor/engine.js", "data/example.json", "index.html", "js/app.js",
    ]
    with pytest.raises(FileExistsError):
        module.package(source, output)


def test_package_refuses_to_write_inside_source(tmp_path):
    (tmp_path / "index.html").write_text("demo")
    with pytest.raises(ValueError):
        module.package(tmp_path, tmp_path / "assets/output")


def test_real_entrypoint_import_map_targets_are_packaged():
    root = Path(__file__).resolve().parents[2]
    html = (root / "index.html").read_text()
    match = re.search(r'<script type="importmap">(.*?)</script>', html, re.DOTALL)
    assert match, "entry point must retain its import map"
    imports = json.loads(match.group(1))["imports"]
    included = {str(p.relative_to(root)) for p in module.static_files(root)}
    for target in imports.values():
        if target.startswith("./"):
            assert target[2:] in included, f"missing runtime module: {target}"


def test_real_experience_asset_references_are_packaged():
    root = Path(__file__).resolve().parents[2]
    included = {str(p.relative_to(root)) for p in module.static_files(root)}

    def visit(value):
        if isinstance(value, dict):
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)
        elif isinstance(value, str) and value.startswith("assets/"):
            assert value in included, f"missing scene asset: {value}"

    visit(json.loads((root / "data/experience.json").read_text()))
