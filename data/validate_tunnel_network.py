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
            route_edges = route.get("edge_ids", [])
            if len(route_nodes) != len(route_edges) + 1:
                errors.append(f"route {route_id}: expected one more node than edge")
                continue
            for index, edge_id in enumerate(route_edges):
                edge = edge_by_id.get(edge_id)
                start, end = route_nodes[index:index + 2]
                if edge is None:
                    errors.append(f"route {route_id}: unknown edge {edge_id}")
                    continue
                if start not in node_by_id or end not in node_by_id:
                    errors.append(f"route {route_id}: unknown node in {start} -> {end}")
                    continue
                forward = edge["from"] == start and edge["to"] == end
                reverse = edge["to"] == start and edge["from"] == end
                if not forward and (not reverse or edge["one_way"]):
                    errors.append(f"route {route_id}: invalid traversal direction for {edge_id}")

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
    print(f"Valid network and routes: {len(network['nodes'])} nodes, {len(network['segments'])} segments, {len(network['graph']['edges'])} graph edges, {len(mission.get('routes', []))} mission routes")


if __name__ == "__main__":
    main()
