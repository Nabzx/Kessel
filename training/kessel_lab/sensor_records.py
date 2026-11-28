"""Strict read-only numeric sensor recordings with causal, gap-aware pairing."""
import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path

import numpy as np

from .observations import CONTRACT, SHAPES, UNITS, adapt
from .range_supervisor import RangeSupervisor
from .runtime import ROOT

SCHEMA = "kessel.sensor-recording-1"
HEADER_KEYS = {"kind","schema","recording_id","source_kind","source_archive","source_member","source_sha256","source_case","clock","calibration","frame","sensor_ids","action_units","decision_s"}
ROW_KEYS = {"kind","use_time_s","observation_packet","applied_action"}
PACKET_KEYS = {"version","clock","calibration","frame","sequence","channels"}
CHANNEL_KEYS = {"sensor_id","units","capture_s","delivery_s","values"}


def encode(value): return json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
def sha(raw): return hashlib.sha256(raw).hexdigest()


def strict_json(raw):
    def unique(items):
        result = {}
        for key,value in items:
            if key in result: raise ValueError("duplicate JSON field")
            result[key] = value
        return result
    return json.loads(raw,object_pairs_hook=unique)


def require_keys(value,expected,name):
    if not isinstance(value,dict) or set(value) != expected: raise ValueError("unexpected or missing "+name+" fields")


def parse(raw):
    if len(raw) > 16*1024**2: raise ValueError("recording exceeds 16 MiB")
    if raw[:2] == b"\x1f\x8b":
        with gzip.GzipFile(fileobj=io.BytesIO(raw)) as stream: decoded = stream.read(16*1024**2+1)
    else: decoded = raw
    if len(decoded) > 16*1024**2: raise ValueError("decoded recording exceeds 16 MiB")
    lines = decoded.splitlines()
    if not 3 <= len(lines) <= 100001: raise ValueError("header and at least two samples required; 100000 sample cap")
    header = strict_json(lines[0]); require_keys(header,HEADER_KEYS,"header")
    if header["kind"] != "header" or header["schema"] != SCHEMA or header["frame"] != CONTRACT["frame"] or header["action_units"] != "normalised" or header["decision_s"] != .1:
        raise ValueError("recording schema, units, frame or decision interval differs")
    if header["source_kind"] not in ("recorded_synthetic","claimed_field_recording"): raise ValueError("explicit recording provenance required")
    for name in ("recording_id","clock","calibration","source_archive","source_member"):
        if not isinstance(header[name],str) or not header[name] or len(header[name]) > 512: raise ValueError("invalid recording identity")
    if not isinstance(header["source_sha256"],str) or len(header["source_sha256"]) != 64 or any(c not in "0123456789abcdef" for c in header["source_sha256"]): raise ValueError("source SHA-256 required")
    require_keys(header["sensor_ids"],set(SHAPES),"sensor identity")
    if any(not isinstance(v,str) or not v for v in header["sensor_ids"].values()): raise ValueError("nonempty sensor IDs required")
    require_keys(header["source_case"],{"seed","family","pattern"},"source case")
    case = header["source_case"]
    if case["seed"] is not None and (isinstance(case["seed"],bool) or not isinstance(case["seed"],int)): raise ValueError("invalid source seed metadata")
    if not isinstance(case["family"],str) or case["pattern"] is not None and not isinstance(case["pattern"],str): raise ValueError("invalid source case metadata")
    rows = []; previous_sequence = previous_time = None; gaps = 0; captures = {}; deliveries = {}
    for line in lines[1:]:
        row = strict_json(line); require_keys(row,ROW_KEYS,"sample")
        if row["kind"] != "sample" or isinstance(row["use_time_s"],bool): raise ValueError("invalid sample clock")
        now = float(row["use_time_s"]); packet = row["observation_packet"]; require_keys(packet,PACKET_KEYS,"packet")
        require_keys(packet["channels"],set(SHAPES),"channel")
        for name in SHAPES:
            channel = packet["channels"][name]; require_keys(channel,CHANNEL_KEYS,"numeric channel")
            if channel["sensor_id"] != header["sensor_ids"][name]: raise ValueError("sensor identity drift")
            for key in ("capture_s","delivery_s"):
                if isinstance(channel[key],bool) or not isinstance(channel[key],(int,float)): raise ValueError("numeric sensor timestamps required")
            if name in captures and (channel["capture_s"] < captures[name]-1e-8 or channel["delivery_s"] < deliveries[name]-1e-8): raise ValueError("reordered channel timestamps")
            captures[name] = channel["capture_s"]; deliveries[name] = channel["delivery_s"]
        observation,health = adapt(packet,clock=header["clock"],calibration=header["calibration"],use_time_s=now)
        observation = RangeSupervisor.validate(observation); sequence = packet["sequence"]
        if abs(observation["proprio"][0,13]-now) > 1e-7: raise ValueError("proprio clock differs from use clock")
        if previous_sequence is not None and (sequence <= previous_sequence or now <= previous_time): raise ValueError("reordered recording")
        contiguous = previous_sequence is not None and sequence == previous_sequence+1 and .09 <= now-previous_time <= .11
        if previous_sequence is not None and not contiguous: gaps += 1
        action = row["applied_action"]
        if action is not None:
            action = np.asarray(action,dtype=float)
            if action.shape != (4,) or not np.isfinite(action).all() or (abs(action) > 1).any(): raise ValueError("four finite normalised recorded commands required")
        rows.append({"sequence":sequence,"use_time_s":now,"observation":observation,"action":action,"contiguous_with_previous":contiguous,"health":health})
        previous_sequence = sequence; previous_time = now
    return header,rows,{"samples":len(rows),"gaps_or_partial_intervals":gaps,"source_kind":header["source_kind"],
                        "validation_scope":"numeric alignment and lineage only; not verified hardware authenticity","machine_interface":False}


def packet(observation,sequence,header):
    now = float(observation["proprio"][13]); age = float(observation["proprio"][11])
    return {"version":CONTRACT["version"],"clock":header["clock"],"frame":header["frame"],"calibration":header["calibration"],"sequence":sequence,
            "channels":{name:{"sensor_id":header["sensor_ids"][name],"units":UNITS[name],"capture_s":now if name == "proprio" else now-age,
                              "delivery_s":now,"values":observation[name]} for name in SHAPES}}


def from_episode(episode,*,archive,member,source_sha256):
    frames = episode["frames"]; case = episode["scenario"]
    if len(frames) > 2 and frames[-1]["observation"]["proprio"][13]-frames[-2]["observation"]["proprio"][13] < .09:
        frames = frames[:-1]
    header = {"kind":"header","schema":SCHEMA,"recording_id":sha((archive+":"+member).encode()),"source_kind":"recorded_synthetic",
              "source_archive":archive,"source_member":member,"source_sha256":source_sha256,
              "source_case":{"seed":case["seed"],"family":case["family"],"pattern":episode.get("pattern")},
              "clock":"synthetic-simulation-seconds","calibration":"default-loader-numeric-v1","frame":CONTRACT["frame"],
              "sensor_ids":{name:"synthetic-"+name for name in SHAPES},"action_units":"normalised","decision_s":.1}
    lines = [encode(header)]
    for index,frame in enumerate(frames):
        observation = frame["observation"]
        lines.append(encode({"kind":"sample","use_time_s":observation["proprio"][13],"observation_packet":packet(observation,index,header),"applied_action":frame.get("action")}))
    return gzip.compress(b"\n".join(lines)+b"\n",mtime=0)


def flat(observation):
    return np.concatenate((observation["proprio"][0],observation["local_height_m"][0].ravel(),observation["range_valid"][0].ravel()))


def pairs(recordings):
    columns = {name:[] for name in ("observation","action","previous_observation","previous_action","history_present","next_observation","recording_id")}
    metadata = []; skipped = 0
    for index,(header,rows) in enumerate(recordings):
        start = len(columns["action"])
        for i,(row,following) in enumerate(zip(rows,rows[1:])):
            if row["action"] is None or not following["contiguous_with_previous"]: skipped += 1; continue
            previous = rows[i-1] if i and row["contiguous_with_previous"] and rows[i-1]["action"] is not None else None
            values = {"observation":flat(row["observation"]),"action":row["action"],"previous_observation":flat(previous["observation"]) if previous else np.zeros(65),
                      "previous_action":previous["action"] if previous else np.zeros(4),"history_present":previous is not None,
                      "next_observation":flat(following["observation"]),"recording_id":index}
            for name,value in values.items(): columns[name].append(value)
        metadata.append({"id":index,"recording_id":header["recording_id"],"start":start,"stop":len(columns["action"]),**header["source_case"],"source_kind":header["source_kind"]})
    return {name:np.asarray(value) for name,value in columns.items()},metadata,skipped


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("path",type=Path); args = parser.parse_args()
    path = args.path.resolve()
    if not path.is_relative_to(ROOT): raise ValueError("recording must be inside the repository")
    if path.stat().st_size > 16*1024**2: raise ValueError("recording exceeds 16 MiB")
    raw = path.read_bytes(); header,rows,stats = parse(raw); data,_,skipped = pairs([(header,rows)])
    print(json.dumps({"recording_id":header["recording_id"],"source_sha256":sha(raw),"causal_pairs":len(data["action"]),"skipped_pairs":skipped,**stats},indent=2))


if __name__ == "__main__": main()
