"""Validate the authored Phase 10 scene, route and operating-data contract."""
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def validate(data):
    errors = []

    def check(condition, message):
        if not condition:
            errors.append(message)

    def asset_paths(value):
        if isinstance(value, dict):
            for child in value.values():
                yield from asset_paths(child)
        elif isinstance(value, list):
            for child in value:
                yield from asset_paths(child)
        elif isinstance(value, str) and value.startswith('assets/'):
            yield value

    check(data['meta']['source'] == 'scripted', 'Experience must declare scripted data')
    for asset in set(asset_paths(data)):
        check((ROOT / asset).is_file(), f'Missing asset: {asset}')
    environments = data['environments']
    check(len({e['id'] for e in environments}) == 5, 'Five unique environments required')
    check([e['id'] for e in environments if e['available']] == ['underground'], 'Only underground is available')
    mine = data['mine']
    check(4 <= len(mine['fleet']['vehicles']) + 1 <= 6, 'Mine needs four to six working machines')
    network = mine['network']
    nodes = {n['id']: n for n in network['nodes']}
    segments = {s['id']: s for s in network['segments']}
    edges = {e['id']: e for e in network['graph']['edges']}
    check(network['graph']['nodes'] == network['nodes'], 'Graph and geometry nodes differ')
    for segment in segments.values():
        for field, position in [('from', segment['centerline_m'][0]), ('to', segment['centerline_m'][-1])]:
            check(position == nodes[segment[field]]['position_m'], f'{segment["id"]}: {field} endpoint mismatch')
        check(all(math.isfinite(c) for p in segment['centerline_m'] for c in p), 'Non-finite centreline')
        # The visible truck envelope must clear the authored rock pillars.
        for x, y, z in segment['centerline_m']:
            for pillar in mine['pillars']:
                px, py, pz = pillar['position']; w, h, d = pillar['size']
                check(not (abs(x-px) < w/2+1.2 and abs(z-pz) < d/2+1.2), f'{segment["id"]}: vehicle intersects pillar')
    for route in mine['routes']:
        for node_key, edge_key in [('node_ids', 'edge_ids'), ('optimised_node_ids', 'optimised_edge_ids')]:
            route_nodes, route_edges = route[node_key], route[edge_key]
            check(len(route_nodes) == len(route_edges)+1, f'{route["id"]}: invalid route length')
            check(route_nodes[0] == route_nodes[-1] == 'draw', f'{route["id"]}: cycle must return to loading')
            for a, b, edge_id in zip(route_nodes, route_nodes[1:], route_edges):
                edge = edges[edge_id]
                check(edge['from'] == a and edge['to'] == b, f'{route["id"]}: wrong-way edge {edge_id}')
    o = data['operations']
    def values(v):
        tonnes_hour = o['fleet_size'] * o['payload_t'] * 60 / v['cycle_minutes'] * v['utilisation']
        hours = o['batch_t'] / tonnes_hour
        hourly_cost = o['fleet_size'] * v['machine_cost_hour'] + o['overhead_gbp_hour']
        return tonnes_hour, hours, hourly_cost / tonnes_hour, hours * hourly_cost
    before, after = values(o['before']), values(o['after'])
    check(math.isclose(before[0], 88) and math.isclose(after[0], 132), 'Throughput arithmetic changed')
    check(round(before[2], 2) == 12.95 and round(after[2], 2) == 8.03, 'GBP cost/tonne arithmetic changed')
    check(round(before[3]-after[3]) == 3467, 'Same-batch GBP savings do not reconcile')
    check(round((before[1]-after[1])*60) == 160, 'Same-batch time savings do not reconcile')
    check(o['before']['idle_percent'] > o['after']['idle_percent'], 'Idle-time comparison must improve')
    training = data['training']; checkpoints = training['checkpoints']; keys = training['keyframes']
    check(training['source'] == 'illustrative', 'Training must be illustrative')
    check(training['episodes'] == checkpoints[-1]['episodes'] == 2400000, 'Training completion count differs')
    check([k['t'] for k in keys] == sorted(set(k['t'] for k in keys)), 'Training keyframes must increase')
    check(keys[0]['t'] == 0 and keys[-1]['t'] == 1, 'Training episode must span the full timeline')
    check(checkpoints[0]['load_t'] == 0 and 0 < checkpoints[-1]['load_t'] <= training['capacity_t'], 'Failure/success payloads invalid')
    check(checkpoints[0]['reward'] < checkpoints[1]['reward'] < checkpoints[2]['reward'], 'Checkpoint rewards must improve')
    check(len(data['kit']['components']) == len({c['id'] for c in data['kit']['components']}) == 7, 'Seven unique kit parts required')
    check(all(all(s > 0 for s in c['size']) for c in data['kit']['components']), 'Kit dimensions must be positive')
    return errors


if __name__ == '__main__':
    issues = validate(json.loads((ROOT / 'data/experience.json').read_text()))
    if issues:
        raise SystemExit('\n'.join(issues))
    print('PASS: assets, route directions/clearance, fleet, GBP arithmetic, learning checkpoints and proposed kit')
