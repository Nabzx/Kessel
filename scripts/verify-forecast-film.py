"""Check film provenance and encoded frame count with the standard library."""
import hashlib
import json
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parents[1]
D = ROOT/"docs/phase-11/forecast-film"


def boxes(raw):
    offset = 0
    while offset < len(raw):
        size,kind = struct.unpack(">I4s",raw[offset:offset+8]); header = 8
        if size == 1: size = struct.unpack(">Q",raw[offset+8:offset+16])[0]; header = 16
        if size == 0: size = len(raw)-offset
        assert size >= header and offset+size <= len(raw)
        yield kind,raw[offset+header:offset+size]
        offset += size
    assert offset == len(raw)


def verify():
    manifest = json.loads((D/"film.json").read_text())
    for name,digest in manifest["files"].items():
        assert (D/name).parent == D and hashlib.sha256((D/name).read_bytes()).hexdigest() == digest
    assert manifest["renderer_sha256"] == hashlib.sha256((ROOT/"scripts/render-forecast-film.py").read_bytes()).hexdigest()
    report_path = ROOT/"docs/phase-11/structured-dynamics-evidence/report.json"
    assert manifest["evidence_report_sha256"] == hashlib.sha256(report_path.read_bytes()).hexdigest()
    report = json.loads(report_path.read_text())
    episode, = [e for e in report["datasets"]["evaluation"]["episodes"] if e["family"] == "nominal"]
    assert episode == manifest["episode"] and manifest["frames"] == episode["stop"]-episode["start"] <= 300
    assert manifest["fps"] == 10 and manifest["render_wall_s"] <= 90
    assert manifest["publication"] == "not_performed" and manifest["manual_visual_acceptance"] == "open"
    film = (D/"synthetic-forecast-comparison.mp4").read_bytes(); assert len(film) <= 16*1024**2
    root = dict(boxes(film)); assert b"ftyp" in root and b"mdat" in root
    movie = dict(boxes(root[b"moov"])); header = movie[b"mvhd"]; assert header[0] == 0
    timescale,duration = struct.unpack(">II",header[12:20])
    assert duration/timescale == manifest["duration_s"] == manifest["frames"]/manifest["fps"]
    track = dict(boxes(movie[b"trak"])); media = dict(boxes(track[b"mdia"])); media_info = dict(boxes(media[b"minf"]))
    samples = dict(boxes(media_info[b"stbl"]))
    assert struct.unpack(">I",samples[b"stsz"][8:12])[0] == manifest["frames"]
    png = (D/"terminal-frame.png").read_bytes(); assert png[:8] == b"\x89PNG\r\n\x1a\n"
    assert struct.unpack(">II",png[16:24]) == (1200,680)
    print("Forecast film: provenance, complete encoded cycle and terminal still verified; human acceptance remains open")


if __name__ == "__main__": verify()
