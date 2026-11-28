import io
import json
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np

from kessel_lab.sensor_runtime import Handler, Session


class SensorRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.session = Session(verification=True)

    def reset(self,**selection):
        return self.session.reset({"family":"nominal","seed":19020,"source":"learned_linear",**selection})

    def test_prediction_uses_only_causal_sensors_before_physics(self):
        s = self.session; self.reset(); events = []; inputs = []
        model = s.run.forecaster.predict; physical = s.run.env.step
        def predict(observation,action,previous,previous_action):
            events.append("forecast"); inputs.append((observation,previous))
            self.assertEqual(set(observation),{"proprio","local_height_m","range_valid"})
            self.assertEqual(observation["proprio"].shape,(1,15))
            return model(observation,action,previous,previous_action)
        def advance(action): events.append("physics"); return physical(action)
        with patch.object(s.run.forecaster,"predict",side_effect=predict),patch.object(s.run.env,"step",side_effect=advance):
            for _ in range(2): s.step({"run_id":s.run_id,"after":s.run.decisions})
        self.assertEqual(events,["forecast","physics","forecast","physics"])
        self.assertIsNone(inputs[0][1]); np.testing.assert_array_equal(inputs[1][1]["proprio"],inputs[0][0]["proprio"])
        trace = s.export_trace(); self.assertFalse(trace["sensor_model_gate_passed"])
        self.assertFalse(trace["frames"][0]["forecast"]["accepted"])
        self.assertEqual(trace["frames"][0]["next_observation"],trace["frames"][1]["observation"])
        self.assertIn("observation",trace["frames"][-1])
        trace["frames"][0]["forecast"]["observation"]["proprio"][0] = 999
        self.assertNotEqual(s.run.records[0]["forecast"]["observation"]["proprio"][0],999)

    def test_stale_requests_and_unsupported_reset_leave_run_unchanged(self):
        s = self.session; original = self.reset()
        for choice in ({"family":"low","seed":19025},{"seed":207400},{"family":"low","pattern":"carry_loss"}):
            with self.assertRaises(ValueError): self.reset(**choice)
            self.assertEqual(original["run_id"],s.run_id)
        play = s.play({"run_id":s.run_id,"after":0}); s.pause({"run_id":s.run_id})
        with self.assertRaises(ValueError): s.step({"run_id":s.run_id,"after":0,"automatic":True,"playback_epoch":play["playback"]["epoch"]})
        self.assertEqual(s.run.decisions,0)

    def test_http_source_and_same_origin_guards_without_binding(self):
        s = self.session; self.reset()
        def request(path,body=None,origin="http://127.0.0.1:8097"):
            handler = Handler.__new__(Handler); output = []; raw = json.dumps(body or {}).encode()
            handler.path = path; handler.server = SimpleNamespace(server_port=8097,session=s)
            handler.rfile = io.BytesIO(raw); handler.headers = {"Host":"127.0.0.1:8097","Origin":origin,"Content-Type":"application/json","Content-Length":str(len(raw))}
            handler.json = lambda status,value:output.append((status,value))
            (handler.do_GET if body is None else handler.do_POST)(); return output[0]
        self.assertFalse(request("/api/info")[1]["sensor_model_gate_passed"])
        self.assertEqual(request("/api/step",{"run_id":s.run_id,"after":0},origin="https://example.com")[0],403)
        self.assertEqual(request("/training/kessel_lab/sensor_model.py")[0],404)
