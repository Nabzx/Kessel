"""Generate a deterministic illustrative underground haul network."""

import argparse
import json
import math
import random
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "data" / "tunnel-network.json"
DEFAULT_SEED = 2026
GENERATOR_VERSION = 3
SECTION_WIDTH_M = 3.0
SECTION_HEIGHT_M = 3.0
RAMP_GRADE_PERCENT = 8.0
HAULAGE_GRADE_PERCENT = 2.75
LEVEL_SPACING_M = 20.0
MINIMUM_RAMP_RADIUS_M = 15.24
LEVEL_COUNT = 3
DECLINE_RUN_PER_LEVEL_M = LEVEL_SPACING_M / (RAMP_GRADE_PERCENT / 100)


def point(x, y, z):
    return [round(x, 3), round(y, 3), round(z, 3)]


def add_node(nodes, node_id, kind, position, level=None):
    nodes.append({
        "id": node_id,
        "kind": kind,
        "position_m": point(*position),
        "level": level,
    })


def polyline_length(points):
    return sum(
        math.dist(start, end)
        for start, end in zip(points, points[1:])
    )


def make_graph(nodes, segments):
    edges = []
    for segment in segments:
        edges.append({
            "id": segment["id"],
            "segment_id": segment["id"],
            "kind": segment["kind"],
            "from": segment["from"],
            "to": segment["to"],
            "length_m": round(polyline_length(segment["centerline_m"]), 3),
            "grade_percent": segment["grade_percent"],
            "width_m": segment["width_m"],
            "one_way": False,
        })
    return {
        "directed": True,
        "nodes": [dict(node) for node in nodes],
        "edges": edges,
    }


def make_network(seed):
    rng = random.Random(seed)
    nodes = []
    segments = []

    add_node(nodes, "portal", "portal", (0, 0, 0))
    add_node(nodes, "tip-surface", "tipping_point", (35, 0, 0))
    segments.append({
        "id": "portal-tipping-bay",
        "kind": "surface_tipping_bay",
        "from": "portal",
        "to": "tip-surface",
        "grade_percent": 0,
        "width_m": 6,
        "height_m": 4,
        "minimum_curve_radius_m": None,
        "centerline_m": [point(0, 0, 0), point(35, 0, 0)],
    })

    level_positions = []
    for index in range(1, LEVEL_COUNT + 1):
        level_y = -LEVEL_SPACING_M * index
        level_z = -DECLINE_RUN_PER_LEVEL_M * index
        level_id = f"L{index}"
        level_positions.append((level_id, level_y, level_z))
        add_node(nodes, f"ramp-{level_id}", "junction", (0, level_y, level_z), level_id)

        previous_id = "portal" if index == 1 else f"ramp-L{index - 1}"
        previous_y = -LEVEL_SPACING_M * (index - 1)
        previous_z = -DECLINE_RUN_PER_LEVEL_M * (index - 1)
        segments.append({
            "id": f"decline-{index}",
            "kind": "decline",
            "from": previous_id,
            "to": f"ramp-{level_id}",
            "grade_percent": -RAMP_GRADE_PERCENT,
            "width_m": SECTION_WIDTH_M,
            "height_m": SECTION_HEIGHT_M,
            "minimum_curve_radius_m": MINIMUM_RAMP_RADIUS_M,
            "centerline_m": [point(0, previous_y, previous_z), point(0, level_y, level_z)],
        })

        if index == 1:
            segments.append({
                "id": "decline-bypass-L1",
                "kind": "decline_bypass",
                "from": "portal",
                "to": "ramp-L1",
                "grade_percent": -RAMP_GRADE_PERCENT,
                "width_m": SECTION_WIDTH_M,
                "height_m": SECTION_HEIGHT_M,
                "minimum_curve_radius_m": MINIMUM_RAMP_RADIUS_M,
                "centerline_m": [
                    point(0, 0, 0),
                    point(8, -5, -62.5),
                    point(8, -15, -187.5),
                    point(0, level_y, level_z),
                ],
            })

    for level_id, level_y, level_z in level_positions:
        half_span = 100.0
        west_y = level_y - HAULAGE_GRADE_PERCENT * half_span / 100
        east_y = level_y + HAULAGE_GRADE_PERCENT * half_span / 100
        west_id = f"haulage-{level_id}-west"
        east_id = f"haulage-{level_id}-east"
        west_point = (-half_span, west_y, level_z)
        east_point = (half_span, east_y, level_z)
        add_node(nodes, west_id, "junction", west_point, level_id)
        add_node(nodes, east_id, "junction", east_point, level_id)
        south_x = -MINIMUM_RAMP_RADIUS_M
        north_x = MINIMUM_RAMP_RADIUS_M
        south_id = f"turn-{level_id}-south"
        north_id = f"turn-{level_id}-north"
        add_node(nodes, south_id, "junction", (south_x, level_y + south_x * HAULAGE_GRADE_PERCENT / 100, level_z), level_id)
        add_node(nodes, north_id, "junction", (north_x, level_y + north_x * HAULAGE_GRADE_PERCENT / 100, level_z), level_id)
        drift_nodes = [
            (west_id, -half_span), (south_id, south_x), (f"ramp-{level_id}", 0),
            (north_id, north_x), (east_id, half_span),
        ]
        for part, ((start_id, start_x), (end_id, end_x)) in enumerate(zip(drift_nodes, drift_nodes[1:]), 1):
            start_y = level_y + start_x * HAULAGE_GRADE_PERCENT / 100
            end_y = level_y + end_x * HAULAGE_GRADE_PERCENT / 100
            segments.append({
                "id": f"haulage-drift-{level_id}-{part}",
                "kind": "haulage_drift",
                "from": start_id,
                "to": end_id,
                "grade_percent": HAULAGE_GRADE_PERCENT,
                "width_m": SECTION_WIDTH_M,
                "height_m": SECTION_HEIGHT_M,
                "minimum_curve_radius_m": None,
                "centerline_m": [point(start_x, start_y, level_z), point(end_x, end_y, level_z)],
            })

        for side, start_x, angle_start, angle_end, side_sign in [
            ("south", -MINIMUM_RAMP_RADIUS_M, 90, 0, -1),
            ("north", MINIMUM_RAMP_RADIUS_M, -90, 0, 1),
        ]:
            radius = MINIMUM_RAMP_RADIUS_M
            start_y = level_y + start_x * HAULAGE_GRADE_PERCENT / 100
            start_id = f"turn-{level_id}-{side}"
            arc_end_id = f"crosscut-{level_id}-{side}-start"
            draw_id = f"draw-point-{level_id}-{side}"
            if side == "south":
                centre_x, centre_z = start_x, level_z - radius
            else:
                centre_x, centre_z = start_x, level_z + radius
            arc_length = radius * math.pi / 2
            arc_points = []
            for step in range(9):
                fraction = step / 8
                degrees = angle_start + (angle_end - angle_start) * fraction
                radians = math.radians(degrees)
                x = centre_x + radius * math.cos(radians)
                z = centre_z + radius * math.sin(radians)
                y = start_y - HAULAGE_GRADE_PERCENT / 100 * arc_length * fraction
                arc_points.append(point(x, y, z))
            arc_end = arc_points[-1]
            arc_end_xyz = tuple(arc_end)
            add_node(nodes, arc_end_id, "junction", arc_end_xyz, level_id)
            segments.append({
                "id": f"junction-turn-{level_id}-{side}",
                "kind": "junction_turn",
                "from": start_id,
                "to": arc_end_id,
                "grade_percent": -HAULAGE_GRADE_PERCENT,
                "width_m": SECTION_WIDTH_M,
                "height_m": SECTION_HEIGHT_M,
                "minimum_curve_radius_m": radius,
                "centerline_m": arc_points,
            })

            length = 60 + rng.randint(-5, 5)
            end_y = arc_end[1] - HAULAGE_GRADE_PERCENT / 100 * length
            end_z = arc_end[2] + side_sign * length
            draw_position = (arc_end[0], end_y, end_z)
            add_node(nodes, draw_id, "draw_point", draw_position, level_id)
            segments.append({
                "id": f"draw-crosscut-{level_id}-{side}",
                "kind": "draw_crosscut",
                "from": arc_end_id,
                "to": draw_id,
                "grade_percent": -HAULAGE_GRADE_PERCENT,
                "width_m": SECTION_WIDTH_M,
                "height_m": SECTION_HEIGHT_M,
                "minimum_curve_radius_m": None,
                "centerline_m": [arc_end, point(*draw_position)],
            })

    return {
        "meta": {
            "id": "kessel-rutongo-illustrative-tunnel-network",
            "source": "scripted",
            "description": "Seeded mechanised-mine scenario, not a Rutongo mine-plan reconstruction.",
            "generator": "data/generate_tunnel_network.py",
            "generator_version": GENERATOR_VERSION,
            "seed": seed,
            "units": "metres",
            "sources": {
                "truck": "https://www.mining.sandvik/globalassets/products/underground-loaders-and-trucks/pdf/th315-specification-sheet-english.pdf",
                "drainage_gradient": "https://www.stantec.com/content/dam/stantec/files/PDFAssets/2020/stantecs-hard-rock-miners-handbook.pdf",
                "rwanda_adit_drainage": "https://www.rmb.gov.rw/fileadmin/user_upload/RMB/Publications/Guidelines/Mining_Safety_Standards.pdf",
                "rutongo_site": "https://trinity-metals.com/en/projects/rutongo-mine",
            },
            "caveat": "Rutongo tunnel positions, levels, extraction method, and present vehicle fleet are not public in the sources reviewed. This is an illustrative mechanised deployment scenario.",
        },
        "design": {
            "cross_section": {
                "profile": "flat_floor_arched_back",
                "width_m": SECTION_WIDTH_M,
                "height_m": SECTION_HEIGHT_M,
            },
            "vehicle_envelope": {
                "reference": "Sandvik TH315, dimensions from the 2023 specification sheet",
                "length_m": 7.71,
                "width_m": 2.274,
                "height_m": 2.395,
                "payload_kg": 15000,
                "clearance_each_side_m": round((SECTION_WIDTH_M - 2.274) / 2, 3),
                "clearance_overhead_m": round(SECTION_HEIGHT_M - 2.395, 3),
            },
            "parameters": {
                "level_count": LEVEL_COUNT,
                "level_spacing_m": LEVEL_SPACING_M,
                "level_spacing_basis": "illustrative scenario input; Rutongo level spacing is not public",
                "decline_grade_percent": RAMP_GRADE_PERCENT,
                "decline_grade_basis": "illustrative scenario input below the TH315 10% loaded performance point; not a certified mine design value",
                "haulage_drainage_grade_percent": HAULAGE_GRADE_PERCENT,
                "drainage_grade_basis": "generic trackless-heading rule of thumb; not a Rutongo-specific standard",
                "minimum_ramp_curve_radius_m": MINIMUM_RAMP_RADIUS_M,
                "curve_radius_basis": "generic 50 ft ramp-heading rule of thumb; not a TH315 swept-path certification",
                "draw_crosscut_length_range_m": [55, 65],
            },
        },
        "levels": [
            {"id": level_id, "level_offset_m": round(level_y, 3), "ramp_station_m": round(level_z, 3)}
            for level_id, level_y, level_z in level_positions
        ],
        "nodes": nodes,
        "segments": segments,
        "graph": make_graph(nodes, segments),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    network = make_network(args.seed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(network, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(network['nodes'])} nodes and {len(network['segments'])} segments to {args.output}")


if __name__ == "__main__":
    main()
