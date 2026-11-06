"""Crop a credited, unitless STL reference without treating it as a mine survey."""

import argparse
import hashlib
import json
import math
from pathlib import Path
import struct

SOURCE = "https://zenodo.org/records/18835599"
ATTRIBUTION = "Hrovat, Simončič, Morano, Kocevska and Javornik, UWB Measurements and 3D Model of a Mine Tunnel, v1.0, CC BY 4.0. Cropped, centred and rotated for reference viewing."


def read_stl(raw):
    if len(raw) < 84:
        raise ValueError("binary STL header is incomplete")
    count = struct.unpack_from("<I", raw, 80)[0]
    if count == 0 or count > 1_000_000 or len(raw) != 84 + count * 50:
        raise ValueError("invalid or unsupported binary STL length/count")
    triangles = []
    for values in struct.iter_unpack("<12fH", raw[84:]):
        positions = values[3:12]
        if not all(math.isfinite(x) for x in positions):
            raise ValueError("STL contains non-finite positions")
        triangles.append(tuple(positions))
    return triangles


def crop_reference(raw, span=12.0):
    if not math.isfinite(span) or span <= 0:
        raise ValueError("span must be finite and positive in source units")
    triangles = read_stl(raw)
    points = [tri[i:i+3] for tri in triangles for i in (0, 3, 6)]
    centre = [math.fsum(v[k] for v in points) / len(points) for k in range(3)]
    xx = math.fsum((v[0]-centre[0])**2 for v in points)
    yy = math.fsum((v[1]-centre[1])**2 for v in points)
    xy = math.fsum((v[0]-centre[0])*(v[1]-centre[1]) for v in points)
    angle = 0.5 * math.atan2(2*xy, xx-yy)
    co, si = math.cos(angle), math.sin(angle)

    def transform(v):
        x, y, z = [v[k]-centre[k] for k in range(3)]
        return (co*x+si*y, z, si*x-co*y)

    projected = [transform(v) for v in points]
    longitudinal = sorted(v[0] for v in projected)
    middle = longitudinal[len(longitudinal)//2]
    kept = []
    for i in range(0, len(projected), 3):
        tri = projected[i:i+3]
        if abs(sum(v[0] for v in tri)/3-middle) <= span/2:
            kept.extend((v[0]-middle, v[1], v[2]) for v in tri)
    if not kept:
        raise ValueError("no triangles in requested reference crop")
    lo = [min(v[k] for v in kept) for k in range(3)]
    hi = [max(v[k] for v in kept) for k in range(3)]
    midpoint = [(lo[k]+hi[k])/2 for k in range(3)]
    flat = [v[k]-midpoint[k] for v in kept for k in range(3)]
    output = struct.pack(f"<{len(flat)}f", *flat)
    meta = {
        "source_url": SOURCE, "licence": "CC-BY-4.0", "attribution": ATTRIBUTION,
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "derived_sha256": hashlib.sha256(output).hexdigest(),
        "source_triangles": len(triangles), "triangles": len(kept)//3,
        "format": "float32-le-positions", "physical_units": None, "crs": None,
        "source_z_is_view_up": "assumption for viewing, not certified",
        "crop_span_source_units": span, "horizontal_rotation_rad": angle,
        "bounds": [[lo[k]-midpoint[k] for k in range(3)],
                   [hi[k]-midpoint[k] for k in range(3)]],
        "bytes": len(output), "reference_only": True,
        "processing": "Keep whole triangles by longitudinal centroid, then centre. Boundaries are uncapped; this is not a collision mesh.",
    }
    return output, meta


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--span", type=float, default=12)
    args = parser.parse_args()
    output, metadata = crop_reference(args.source.read_bytes(), args.span)
    for path in (args.output.with_suffix(".bin"), args.output.with_suffix(".json")):
        if path.exists():
            parser.error("output exists; choose a new path")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.with_suffix(".bin").write_bytes(output)
    args.output.with_suffix(".json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(json.dumps(metadata, indent=2))
