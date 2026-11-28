import copy
import gzip
import json
import unittest

import numpy as np

from kessel_lab.sensor_records import from_episode, parse, pairs
from kessel_lab.sensor_model import SensorModel, flatten, features


def recording():
    frames = []
    for i in range(3):
        p = np.zeros(15); p[3] = 1; p[12] = 1; p[13] = i*.1
        obs = {"proprio":p.tolist(),"local_height_m":np.full((5,5),.2).tolist(),"range_valid":np.ones((5,5)).tolist()}
        frame = {"observation":obs,"state":[99.]*102}
        if i < 2: frame["action"] = [.2,0,0,0]
        frames.append(frame)
    episode = {"scenario":{"seed":19020,"family":"nominal"},"frames":frames}
    return episode,from_episode(episode,archive="recorded-test.zip",member="sample.json.gz",source_sha256="0"*64)


def modify(raw,change):
    values = [json.loads(v) for v in gzip.decompress(raw).splitlines()]; change(values)
    return b"\n".join(json.dumps(v,allow_nan=False).encode() for v in values)+b"\n"


class SensorRecordingTests(unittest.TestCase):
    def test_privileged_source_state_cannot_change_exported_sensor_stream(self):
        episode,raw = recording(); changed = copy.deepcopy(episode)
        for frame in changed["frames"]: frame["state"] = [-500.]*102; frame["friction"] = 100
        self.assertEqual(from_episode(changed,archive="recorded-test.zip",member="sample.json.gz",source_sha256="0"*64),raw)
        header,rows,stats = parse(raw); data,_,skipped = pairs([(header,rows)])
        self.assertEqual(len(data["action"]),2); self.assertEqual(skipped,0); self.assertFalse(stats["machine_interface"])

    def test_unknown_fields_calibration_units_and_future_timestamps_are_rejected(self):
        _,raw = recording()
        changes = (lambda v:v[1].update(state=[0]*102),
                   lambda v:v[1]["observation_packet"].update(calibration="other"),
                   lambda v:v[1]["observation_packet"]["channels"]["local_height_m"].update(units="cm"),
                   lambda v:v[1]["observation_packet"]["channels"]["proprio"].update(capture_s=1))
        for change in changes:
            with self.assertRaises(ValueError): parse(modify(raw,change))

    def test_gaps_break_pairs_and_stale_range_never_becomes_valid_geometry(self):
        _,raw = recording()
        header,rows,stats = parse(modify(raw,lambda v:v[3]["observation_packet"].update(sequence=4)))
        data,_,skipped = pairs([(header,rows)])
        self.assertEqual(len(data["action"]),1); self.assertEqual(skipped,1)
        def invalid(v):
            v[1]["observation_packet"]["channels"]["range_valid"]["values"][0][0] = 0
            v[1]["observation_packet"]["channels"]["local_height_m"]["values"][0][0] = 999
        _,rows,_ = parse(modify(raw,invalid))
        self.assertEqual(rows[0]["observation"]["local_height_m"][0,0,0],0)

    def test_field_header_is_a_provenance_claim_not_hardware_validation(self):
        _,raw = recording(); _,_,stats = parse(modify(raw,lambda v:v[0].update(source_kind="claimed_field_recording")))
        self.assertIn("not verified hardware",stats["validation_scope"])

    def test_model_receives_no_state_and_drops_absolute_position_and_time_context(self):
        _,raw = recording(); header,rows,_ = parse(raw); data,_,_ = pairs([(header,rows)])
        a = features(data["observation"],data["action"],data["previous_observation"],data["previous_action"],data["history_present"])
        current = data["observation"].copy(); previous = data["previous_observation"].copy()
        current[:,:2] += 100; previous[:,:2] += 100; current[:,13] += 500; previous[:,13] += 500
        b = features(current,data["action"],previous,data["previous_action"],data["history_present"])
        np.testing.assert_array_equal(a,b)
        model = SensorModel(np.ones(15),np.ones(25)); obs = rows[0]["observation"]
        with self.assertRaises(ValueError): model.predict({**obs,"state":np.zeros((1,102))},[[0,0,0,0]])
