"""Prepare a bounded local review kit. Never starts a browser or publishes."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]


def prepare(output):
    output = output.resolve(); allowed = (ROOT/".local").resolve()
    if not output.is_relative_to(allowed) or output == allowed:
        raise ValueError("handover must be a new child of repo-local .local")
    started = time.monotonic(); output.mkdir(parents=True,exist_ok=False)
    spec = importlib.util.spec_from_file_location("static_candidate",ROOT/"scripts/prepare-release-candidate.py")
    package = importlib.util.module_from_spec(spec); spec.loader.exec_module(package)
    package.prepare(output/"static")
    copies = {"docs/HOSTING.md":"HOSTING.md","docs/RECORDING.md":"RECORDING.md",
              "docs/phase-11/structured-dynamics.md":"structured-dynamics.md","docs/phase-11/collection-coverage.md":"collection-coverage.md"}
    for name in ("harvest-repair.md","harvest-qualification.md"):
        source = ROOT/"docs/phase-11"/name
        if source.is_file(): copies[str(source.relative_to(ROOT))] = name
    film_dir = ROOT/"docs/phase-11/forecast-film"
    film = json.loads((film_dir/"film.json").read_text())
    for name,digest in film["files"].items():
        source = film_dir/name
        if source.parent != film_dir or hashlib.sha256(source.read_bytes()).hexdigest() != digest:
            raise ValueError("film manifest differs")
        copies[str(source.relative_to(ROOT))] = "film/"+name
    copies[str((film_dir/"film.json").relative_to(ROOT))] = "film/film.json"
    for source,target in copies.items():
        if time.monotonic()-started > 45: raise TimeoutError("handover exceeded 45 seconds")
        destination = output/target; destination.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(ROOT/source,destination)
    reports = {name:json.loads((ROOT/f"docs/phase-11/{name}/report.json").read_text()) for name in
               ("progress-validation-evidence","linear-feedback-evidence","structured-dynamics-evidence","collection-coverage-evidence")}
    summary = {"source_commit":subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),
               "progress_validation_passed":reports["progress-validation-evidence"]["gate_passed"],
               "linear_feedback_full_gate_passed":reports["linear-feedback-evidence"]["gate_passed"],
               "forecast_eligible_methods":reports["structured-dynamics-evidence"]["forecast_eligible_methods"],
               "collection_full_gate_passed":reports["collection-coverage-evidence"]["gate_passed"],
               "manual_checks":{"274":"real background/foreground and readability remain open","351":"maintainer visual judgement remains open",
                                "385":"maintainer visual judgement remains open","276":"real walkthrough capture and release acceptance remain open"},
               "publication":"not_performed","browsers_started":0,"services_started":0}
    current = ROOT/"docs/phase-11/harvest-qualification-evidence/fresh/report.json"
    if current.is_file():
        qualified = json.loads(current.read_text())
        summary["current_harvest"] = {"report_sha256":hashlib.sha256(current.read_bytes()).hexdigest(),
            "complete":qualified["complete"],"supported_envelope_gate":qualified.get("supported_envelope_gate",False),
            "start_guard_qualified":qualified.get("start_guard_qualified",False),"forecast_gate":qualified.get("forecast",{}).get("gate_passed",False),
            "original_full_delivery_gate":qualified.get("original_full_gate",False),"runtime_admitted":qualified["runtime_admitted"],
            "scope":"synthetic: >=3200 kg above blade and >=200 N empty forward margin; eight initial-screened cases per family",
            "start_refusal_acceptance":"pending; delivery and refusal remain separate"}
        summary["historical_gate_fields"] = ["linear_feedback_full_gate_passed","collection_full_gate_passed"]
        decision_path = ROOT/"docs/phase-11/harvest-qualification-evidence/start-refusal-acceptance.json"
        if decision_path.is_file():
            decision = json.loads(decision_path.read_text())
            if decision["status"] != "accepted" or decision["qualification_report_sha256"] != summary["current_harvest"]["report_sha256"]:
                raise ValueError("refusal decision does not match this qualification")
            summary["current_harvest"]["start_refusal_acceptance"] = "accepted by maintainer "+decision["decision_date"]+"; delivery and refusal remain separate"
    (output/"status.json").write_text(json.dumps(summary,indent=2)+"\n")
    (output/"README.txt").write_text("Kessel review handover\n\n"
        "static/kessel-static-candidate.zip: verified concept presentation, not a deployed site.\n"
        "film/synthetic-forecast-comparison.mp4: complete recorded synthetic cycle and saved hybrid predictions.\n"
        "film/terminal-frame.png: final comparison still.\n"
        "RECORDING.md: core/technical routes and missing native review.\n"
        "HOSTING.md: concrete publication and rollback procedure after acceptance.\n"
        "status.json: passed and failed gates, source commit and open human criteria.\n\n"
        "When present, current_harvest gives the later scoped qualification; historical gate fields preserve earlier failed studies.\n"
        "The existing full visual review remains in docs/phase-11/acceptance-review/index.html in the repository.\n"
        "This kit does not record a new browser walkthrough, accept visuals or publish anything.\n")
    paths = sorted(p for p in output.rglob("*") if p.is_file())
    total = sum(p.stat().st_size for p in paths)
    if total > 80*1024**2: raise ValueError("handover exceeds 80 MiB")
    manifest = {"kind":"kessel-local-review-handover-v1","source_commit":summary["source_commit"],"uncompressed_bytes":total,
                "wall_s":time.monotonic()-started,"publication":"not_performed","visual_acceptance":"open",
                "files":{str(p.relative_to(output)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}}
    (output/"handover.json").write_text(json.dumps(manifest,indent=2)+"\n")
    for name,digest in manifest["files"].items():
        if hashlib.sha256((output/name).read_bytes()).hexdigest() != digest: raise ValueError("handover differs: "+name)
    print(json.dumps({"handover":str(output.relative_to(ROOT)),"verified_files":len(paths),"bytes":total,"wall_s":manifest["wall_s"]}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--output",required=True,type=Path)
    prepare(parser.parse_args().output)
