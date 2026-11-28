"""Independently reconstruct sensor lineage, causal pairs and qualification gates."""
import gzip
import importlib.util
import json
import math
from pathlib import Path
import statistics
import zipfile

ROOT = Path(__file__).resolve().parents[1]
D = ROOT/"docs/phase-11/sensor-forecast-v2-evidence"


def module(name,path):
    spec = importlib.util.spec_from_file_location(name,ROOT/path)
    result = importlib.util.module_from_spec(spec); spec.loader.exec_module(result)
    return result


base = module("progress_check","scripts/verify-progress-control.py")
numeric = module("refit_check","scripts/verify-forecast-refit.py")
DATA_KEYS = ("observation","action","previous_observation","previous_action","history_present","next_observation","recording_id")


def observation(row,header):
    assert set(row) == {"kind","use_time_s","observation_packet","applied_action"}
    packet = row["observation_packet"]; now = row["use_time_s"]
    assert set(packet) == {"version","clock","calibration","frame","sequence","channels"}
    assert packet["clock"] == header["clock"] and packet["calibration"] == header["calibration"] and packet["frame"] == header["frame"]
    channels = packet["channels"]; assert set(channels) == {"proprio","local_height_m","range_valid"}
    for name,c in channels.items():
        assert set(c) == {"sensor_id","units","capture_s","delivery_s","values"}
        assert c["sensor_id"] == header["sensor_ids"][name] and c["capture_s"] <= c["delivery_s"] <= now
        assert c["units"] == {"proprio":"proprio-fields-v1","local_height_m":"m","range_valid":"boolean"}[name]
    p = channels["proprio"]["values"].copy(); h = sum(channels["local_height_m"]["values"],[]); mask = sum(channels["range_valid"]["values"],[])
    assert len(p) == 15 and len(h) == len(mask) == 25 and all(v in (0,1) for v in mask)
    assert now-channels["proprio"]["capture_s"] <= .2
    age = max(now-channels[n]["capture_s"] for n in ("local_height_m","range_valid"))
    if age > .2: mask = [0]*25
    p[11] = age; p[12] = float(age <= .2 and any(mask))
    assert p[13] == now and all(math.isfinite(v) for v in p+h+mask)
    if not p[12]: mask = [0]*25
    return p+[a*b for a,b in zip(h,mask)]+mask


def errors(data,pred):
    result = []
    for y,p in zip(data["next_observation"],pred["observation"]):
        assert len(y) == len(p) == 65 and all(math.isfinite(v) for v in p)
        valid = sum(y[40:65]); height = sum(abs(a-b)*m for a,b,m in zip(p[15:40],y[15:40],y[40:65]))/max(1,valid)
        pos = math.dist(p[:2],y[:2]); speed = abs(p[4]-y[4]); load = abs(p[8]-y[8])
        result.append(dict(position=pos,speed=speed,carried=load,height=height,height_valid=valid > 0,
            validity_brier=sum((a-b)**2 for a,b in zip(p[40:65],y[40:65]))/25,freshness_brier=(p[12]-y[12])**2,
            high=pos > .05 or speed > .05 or load > 50 or height > .05))
    return result


def metric(rows,selected=None):
    chosen = rows if selected is None else [r for r,s in zip(rows,selected) if s]
    result = {"rows":len(chosen),"target_valid_height_rows":sum(r["height_valid"] for r in chosen)}
    for key in ("position","speed","carried","height","validity_brier","freshness_brier","high"):
        values = [r[key] for r in chosen if key != "height" or r["height_valid"]]
        result[key+"_mean"] = statistics.mean(values) if values else None
    return result


def compare(actual,expected):
    assert set(actual) == set(expected)
    for key,a in actual.items():
        if a is None: assert expected[key] is None
        else: numeric.close(a,expected[key])


def percentile(values,q):
    values = sorted(values); at = (len(values)-1)*q/100; lo = int(at); hi = math.ceil(at)
    return values[lo]+(values[hi]-values[lo])*(at-lo)


def verify():
    failed = ROOT/"docs/phase-11/sensor-forecast-evidence"
    for path,digest in json.loads((failed/"files.json").read_text()).items(): assert base.sha((ROOT/path).read_bytes()) == digest
    rejection = json.loads((failed/"report.json").read_text())
    assert not rejection["complete"] and rejection["errors"] == ["ValueError: reordered channel timestamps"] and rejection["cost"]["counts"]["updates"] == 0
    r = base.capsule(D,current=True); p = r["plan"]
    assert not r["privileged_inputs"] and not r["runtime_admitted"] and r["physical_queries"] == 0
    assert not p["field_recordings_supplied"] and p["source_kind"] == "recorded_synthetic"
    assert r["cost"]["wall_s"] <= 240 and r["cost"]["counts"] == {"updates":2250}
    for path,digest in p["source_archives"].items(): assert base.sha((ROOT/path).read_bytes()) == digest
    training = json.loads((D/"training.json").read_text())
    assert training["updates"] == 2250 and training["input_dimension"] == 139 and training["target_dimension"] == 65
    assert not training["privileged_inputs"] and training["simulator_queries"] == 0
    assert len(training["members"]) == 3 and [m["seed"] for m in training["members"]] == [101,211,307]
    assert all(len(m["history"]) == 750 and [h["update"] for h in m["history"]] == list(range(1,751)) for m in training["members"])
    identities = set(); bases = {}; split_values = {}; total_omitted = 0
    with zipfile.ZipFile(D/"recordings.zip") as archive:
        assert set(archive.namelist()) == {c["member"] for c in r["recordings"]}
        for split,expected_count in (("train",26),("validation",18),("evaluation",152)):
            data = numeric.npz(D/f"{split}.npz",DATA_KEYS); info = r["datasets"][split]; offset = skipped = 0
            with zipfile.ZipFile(D/f"{split}.npz") as arrays: assert set(arrays.namelist()) == {n+".npy" for n in DATA_KEYS}
            cases = [c for c in r["recordings"] if c["split"] == split]
            assert len(cases) == len(info["episodes"]) == expected_count
            for index,(case,meta) in enumerate(zip(cases,info["episodes"])):
                raw = archive.read(case["member"]); assert base.sha(raw) == case["sha256"]
                header,*rows = [json.loads(line) for line in gzip.decompress(raw).splitlines()]
                assert header == case["header"] and header["source_kind"] == "recorded_synthetic" and header["recording_id"] not in identities
                identities.add(header["recording_id"]); seed = header["source_case"]["seed"]
                assert seed in p[{"train":"training_bases","validation":"validation_bases","evaluation":"evaluation_bases"}[split]]
                assert seed not in bases or bases[seed] == split; bases[seed] = split
                with zipfile.ZipFile(ROOT/header["source_archive"]) as original:
                    source_raw = original.read(header["source_member"]); assert base.sha(source_raw) == header["source_sha256"]
                    frames = json.loads(gzip.decompress(source_raw))["frames"]
                omit = int(len(frames) > 2 and frames[-1]["observation"]["proprio"][13]-frames[-2]["observation"]["proprio"][13] < .09)
                assert omit == case["omitted_partial_terminal_snapshots"] and len(rows) == len(frames)-omit
                total_omitted += omit
                values = [observation(row,header) for row in rows]
                assert meta["start"] == offset and meta["id"] == index and meta["recording_id"] == header["recording_id"]
                for i,row in enumerate(rows):
                    f = frames[i]; packet = row["observation_packet"]
                    assert packet["sequence"] == i and row["applied_action"] == f.get("action")
                    assert all(packet["channels"][n]["values"] == f["observation"][n] for n in packet["channels"])
                    if i == len(rows)-1: continue
                    contiguous = rows[i+1]["observation_packet"]["sequence"] == i+1 and .09 <= rows[i+1]["use_time_s"]-row["use_time_s"] <= .11
                    if row["applied_action"] is None or not contiguous: skipped += 1; continue
                    past = i > 0 and .09 <= row["use_time_s"]-rows[i-1]["use_time_s"] <= .11 and rows[i-1]["applied_action"] is not None
                    expected = {"observation":values[i],"next_observation":values[i+1],"action":row["applied_action"],"recording_id":index,
                        "history_present":past,"previous_observation":values[i-1] if past else [0]*65,"previous_action":rows[i-1]["applied_action"] if past else [0]*4}
                    for key,value in expected.items(): assert data[key][offset] == value,(split,index,i,key)
                    offset += 1
                assert meta["stop"] == offset
            assert offset == info["rows"] == len(data["action"]) and skipped == info["skipped_intervals"]
            if split == "train":
                floors = [.005,.005,.001,.001,.01,.001,.001,.001,1,.01,.01,.02,1,1,.01]
                ps = [max(statistics.pstdev(y[j]-x[j] for x,y in zip(data["observation"],data["next_observation"])),floors[j]) for j in range(15)]; ps[12:14] = [1,1]
                hs = [max(statistics.pstdev(y[j]-x[j] for x,y in zip(data["observation"],data["next_observation"])),.01) for j in range(15,40)]
                for a,b in zip(ps+hs,training["proprio_scale"]+training["height_scale"]): numeric.close(a,b)
                continue
            pred = numeric.npz(D/f"{split}-predictions.npz",("observation","disagreement","input_usable"))
            assert len(pred["observation"]) == offset
            usable = [bool(x[12] == 1 and x[11] <= .2+1e-9 and sum(x[40:65]) >= 5) for x in data["observation"]]
            assert usable == pred["input_usable"] and all(math.isfinite(x) and x >= 0 for x in pred["disagreement"])
            assert all(min(x[15:40]) >= 0 and all(0 <= v <= 1 for v in x[40:65]) for x in pred["observation"])
            measured = errors(data,pred); split_values[split] = (data,pred,measured)
    vd,vp,ve = split_values["validation"]; trades = []
    for q in (10,25,50,75,90,100):
        threshold = percentile([s for s,u in zip(vp["disagreement"],vp["input_usable"]) if u],q)
        selected = [u and s <= threshold for u,s in zip(vp["input_usable"],vp["disagreement"])]
        trades.append(dict(percentile=q,threshold=threshold,accepted=sum(selected),coverage=sum(selected)/len(selected),high_error_fraction=metric(ve,selected)["high_mean"]))
    for a,b in zip(trades,r["calibration"]["tradeoffs"]): compare(a,b)
    chosen = max((t for t in trades if t["accepted"] >= 100 and t["high_error_fraction"] <= .1),key=lambda t:t["coverage"],default=None)
    threshold = chosen["threshold"] if chosen else None
    assert threshold == r["calibration"]["threshold"]
    ed,ep,ee = split_values["evaluation"]
    selected = [threshold is not None and u and s <= threshold for u,s in zip(ep["input_usable"],ep["disagreement"])]
    accepted = metric(ee,selected); persistence = metric(errors(ed,{"observation":ed["observation"]}),selected)
    compare(metric(ee),r["raw"]); compare(accepted,r["accepted"]); compare(persistence,r["persistence_same_accepted"])
    benefit = any(accepted[k] is not None and persistence[k] and accepted[k] <= .9*persistence[k] for k in ("speed_mean","height_mean"))
    assert r["beats_persistence"] == bool(benefit)
    assert r["finite_nonnegative_probability_bounds"]
    assert r["gate_passed"] == bool(accepted["rows"] >= 100 and accepted["high_mean"] <= .1 and benefit)
    for family in r["families"]:
        ids = {e["id"] for e in r["datasets"]["evaluation"]["episodes"] if e["family"] == family["family"]}
        mask = [i in ids for i in ed["recording_id"]]; accepted_family = metric(ee,[a and b for a,b in zip(mask,selected)])
        compare(accepted_family,family["accepted"])
        assert family["supported"] == (accepted_family["rows"] >= 20 and accepted_family["high_mean"] <= .1)
    print(f"Sensor: 196 synthetic recordings, causal split lineage and saved errors verified; {total_omitted} partial terminal snapshots omitted; gate {r['gate_passed']}")


if __name__ == "__main__": verify()
