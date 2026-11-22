"""Check the repository-only review, its source identities and retained evidence."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
D = ROOT / "docs/phase-11/acceptance-review"


def verify():
    review = json.loads((D / "review.json").read_text())
    assert review["visual_acceptance"] == "open"
    assert sum(r["seconds"] for r in review["routes"]["core"]) == 60
    assert sum(r["seconds"] for r in review["routes"]["technical"]) == 90
    assets = {r["image"] for rows in review["routes"].values() for r in rows}
    assets |= {r[k] for r in review["comparisons"] for k in ("previous", "current")}
    for name in assets:
        p = (D / name).resolve()
        assert p.is_relative_to(ROOT) and p.is_file(), name
    focus = json.loads((D / "evidence/focus.json").read_text())
    assert focus["mode"] == "headless" and not focus["desktopAutomation"]
    assert focus["timeoutSeconds"] == 45
    assert focus["dialogReturnFocus"] and focus["reducedMotionEntrance"] and focus["normalMotionEarlyFocus"]
    assert not focus["errors"]
    contrast = json.loads((D / "evidence/contrast.json").read_text())
    assert len(contrast["profiles"]) == 3
    assert all(r["pass"] for p in contrast["profiles"] for s in p["sections"] for r in s["rows"])
    page = json.loads((D / "evidence/review-page.json").read_text())
    assert page["headless"] and not page["desktopAutomation"] and page["timeoutSeconds"] == 30
    assert page["mainSeconds"] == 60 and page["technicalSeconds"] == 90 and page["pauseHolds"]
    assert not page["errors"] and not page["narrowOverflow"]
    assert not (ROOT / "scripts/research/native-review-browser.cjs").exists()
    assert not (ROOT / "scripts/research/verify-native-background.cjs").exists()
    for name in ("review-focus.cjs", "verify-review-page.cjs"):
        script = (ROOT / "scripts/research" / name).read_text()
        assert "headless:true" in script and "headless:false" not in script
    manifest = json.loads((D / "evidence/files.json").read_text())
    for name, expected in manifest.items():
        p = (ROOT / name).resolve()
        assert p.is_relative_to(ROOT)
        assert hashlib.sha256(p.read_bytes()).hexdigest() == expected, name
    print("PASS: repo-only review, storyboard timing, bounded headless checks and source hashes")


if __name__ == "__main__":
    verify()
