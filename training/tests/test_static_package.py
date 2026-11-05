import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location("static_package", Path(__file__).parents[2] / "scripts/package-static.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_package_excludes_experiment_files_and_preserves_credits(tmp_path):
    source = tmp_path / "source"
    paths = ["index.html", "LICENSE", "js/app.js", "assets/model.bin",
             "assets/README.md", "assets/.private/image.png", "data/example.json",
             "data/generator.py", "training/model.bin", ".venv/tool.py", ".git/config"]
    for name in paths:
        file = source / name
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(name)
    (source / "assets/leak.bin").symlink_to(source / "training/model.bin")
    output = tmp_path / "public"
    count, _ = module.package(source, output)
    assert count == 6
    assert sorted(str(p.relative_to(output)) for p in output.rglob("*") if p.is_file()) == [
        "LICENSE", "assets/README.md", "assets/model.bin", "data/example.json", "index.html", "js/app.js",
    ]
    with pytest.raises(FileExistsError):
        module.package(source, output)


def test_package_refuses_to_write_inside_source(tmp_path):
    (tmp_path / "index.html").write_text("demo")
    with pytest.raises(ValueError):
        module.package(tmp_path, tmp_path / "assets/output")
