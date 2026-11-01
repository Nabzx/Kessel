"""Check graph references and geometry alignment in a tunnel network JSON file."""

import argparse
import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "data" / "tunnel-network.json"


def close_points(left, right, tolerance=0.002):
    return all(abs(a - b) <= tolerance for a, b in zip(left, right))


def polyline_length(points):
    return sum(math.dist(start, end) for start, end in zip(points, points[1:]))


def validate(network, mission=None):
    errors = []
    nodes = network.get("nodes", [])
    segments = network.get("segments", [])
    graph = network.get("graph", {})
    node_by_id = {node.get("id"): node for node in nodes}
    segment_by_id = {segment.get("id"): segment for segment in segments}

    if len(node_by_id) != len(nodes):
        errors.append("geometry node IDs must be unique")
    if len(segment_by_id) != len(segments):
        errors.append("geometry segment IDs must be unique")
    if graph.get("directed") is not True:
        errors.append("graph.directed must be true")
    if graph.get("nodes") != nodes:
        errors.append("graph nodes must exactly match geometry nodes")

    edges = graph.get("edges", [])
    edge_by_id = {edge.get("id"): edge for edge in edges}
    if len(edge_by_id) != len(edges):
        errors.append("graph edge IDs must be unique")
    if set(edge_by_id) != set(segment_by_id):
        errors.append("graph edges must map one-to-one to geometry segments")

    for segment_id, segment in segment_by_id.items():
        edge = edge_by_id.get(segment_id)
        if edge is None:
            continue
        for endpoint in ("from", "to"):
            node_id = segment.get(endpoint)
            if node_id not in node_by_id:
                errors.append(f"segment {segment_id}: unknown {endpoint} node {node_id}")
                continue
            endpoint_position = segment["centerline_m"][0 if endpoint == "from" else -1]
            if not close_points(endpoint_position, node_by_id[node_id]["position_m"]):
                errors.append(f"segment {segment_id}: {endpoint} does not match its node position")

        if edge.get("segment_id") != segment_id:
            errors.append(f"edge {segment_id}: segment_id does not match")
        for field in ("kind", "from", "to", "grade_percent", "width_m"):
            if edge.get(field) != segment.get(field):
                errors.append(f"edge {segment_id}: {field} does not match geometry")
        if not isinstance(edge.get("one_way"), bool):
            errors.append(f"edge {segment_id}: one_way must be boolean")
        expected_length = round(polyline_length(segment["centerline_m"]), 3)
        if edge.get("length_m") != expected_length:
            errors.append(f"edge {segment_id}: length_m does not match centerline length")

    if mission is not None:
        routes = mission.get("routes", [])
        route_ids = [route.get("id") for route in routes]
        if len(set(route_ids)) != len(route_ids):
            errors.append("mission route IDs must be unique")
        for route in routes:
            route_id = route.get("id", "<unnamed>")
            route_nodes = route.get("node_ids", [])
            for field in ("edge_ids", "optimised_edge_ids"):
                if field not in route:
                    continue
                route_edges = route[field]
                if len(route_nodes) != len(route_edges) + 1:
                    errors.append(f"route {route_id} {field}: expected one more node than edge")
                    continue
                for index, edge_id in enumerate(route_edges):
                    edge = edge_by_id.get(edge_id)
                    start, end = route_nodes[index:index + 2]
                    if edge is None:
                        errors.append(f"route {route_id} {field}: unknown edge {edge_id}")
                        continue
                    if start not in node_by_id or end not in node_by_id:
                        errors.append(f"route {route_id} {field}: unknown node in {start} -> {end}")
                        continue
                    forward = edge["from"] == start and edge["to"] == end
                    reverse = edge["to"] == start and edge["from"] == end
                    if not forward and (not reverse or edge["one_way"]):
                        errors.append(f"route {route_id} {field}: invalid traversal direction for {edge_id}")

        fleet_ids = {vehicle.get("id") for vehicle in mission.get("fleet", {}).get("vehicles", [])}
        route_vehicle_ids = {route.get("vehicle_id") for route in routes}
        if fleet_ids != route_vehicle_ids:
            errors.append("fleet vehicle IDs must match mission route vehicle IDs")
        fleet = mission.get("fleet", {})
        for phase in ("loading", "tipping"):
            if fleet.get("dwell_seconds", {}).get(phase, 0) <= 0:
                errors.append(f"fleet must define a positive {phase} dwell")
        if fleet.get("inspection_time_scale", 0) <= 0:
            errors.append("fleet inspection_time_scale must be positive")
        prediction = mission.get("prediction_preview", {})
        samples = prediction.get("samples", [])
        if prediction.get("source") != "scripted" or not samples:
            errors.append("prediction preview must identify its scripted samples")
        if any(sample.get("horizon_seconds", 0) <= 0 or sample.get("error_m", -1) < 0 for sample in samples):
            errors.append("prediction samples need positive horizons and non-negative errors")
        for route in routes:
            node_ids = route.get("node_ids", [])
            if not node_ids or node_ids[0] != node_ids[-1]:
                errors.append("haul routes must return to their loading point")
            elif node_by_id.get(node_ids[0], {}).get("kind") != "draw_point":
                errors.append("haul routes must begin at a draw point")
            if not any(node_by_id.get(node_id, {}).get("kind") == "tipping_point" for node_id in node_ids):
                errors.append("haul routes must include a tipping point")
        trace = mission.get("optimiser_trace", {})
        steps = trace.get("steps", [])
        if trace.get("source") != "scripted":
            errors.append("the concept optimiser trace must be labelled scripted")
        if not steps or steps[-1].get("iterations") != trace.get("run_count"):
            errors.append("the final scripted optimiser step must match run_count")
        model_reference = mission.get("assets", {}).get("fleet_vehicle_model")
        if not model_reference or not (ROOT / model_reference).is_file():
            errors.append("the configured fleet vehicle model asset must exist")
        else:
            model = json.loads((ROOT / model_reference).read_text(encoding="utf-8"))
            material_names = set(model.get("materials", {}))
            if any(part.get("material") not in material_names for part in model.get("parts", [])):
                errors.append("fleet vehicle parts must refer to defined materials")
            if len(model.get("forward_axis", [])) != 3:
                errors.append("fleet vehicle model must define a three-axis forward direction")

    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--mission", type=Path, default=ROOT / "data" / "mission.json")
    args = parser.parse_args()
    network = json.loads(args.path.read_text(encoding="utf-8"))
    mission = json.loads(args.mission.read_text(encoding="utf-8"))
    errors = validate(network, mission)
    if errors:
        raise SystemExit("Invalid tunnel network:\n- " + "\n- ".join(errors))
    print(f"Valid mission: {len(network['nodes'])} nodes, {len(network['segments'])} segments, {len(network['graph']['edges'])} graph edges, {len(mission.get('routes', []))} routes, {len(mission.get('fleet', {}).get('vehicles', []))} vehicles")


if __name__ == "__main__":
    main()
