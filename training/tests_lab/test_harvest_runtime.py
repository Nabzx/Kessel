import copy
import io
import json
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from kessel_lab.harvest_runtime import Handler, Session


class HarvestRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.session = Session(verification=True)

    def reset(self,**kwargs): return self.session.reset({"family":"nominal","source":"learned_linear","seed":19020,**kwargs})

    def test_forecast_precedes_physics_and_export_is_an_independent_snapshot(self):
        s = self.session; self.reset(); events = []
        predict = s.run.forecaster.predict; step = s.run.env.step
        def prediction(*args): events.append("forecast"); return predict(*args)
        def physical(*args): events.append("physics"); return step(*args)
        with patch.object(s.run.forecaster,"predict",side_effect=prediction),patch.object(s.run.env,"step",side_effect=physical):
            result = s.step({"run_id":s.run_id,"after":0})
        self.assertEqual(events,["forecast","physics"])
        self.assertEqual(result["frames"][0]["forecast"]["produced_at_s"],0)
        self.assertFalse(result["frames"][0]["forecast"]["influences_action"])
        exported = s.export_trace(); json.dumps(exported,allow_nan=False)
        exported["frames"][0]["forecast"]["state"][0] = 999
        self.assertNotEqual(s.run.records[0]["forecast"]["state"][0],999)

    def test_admission_failure_does_not_replace_or_step_the_current_run(self):
        s = self.session; self.reset(); identity = s.run_id
        for selection in ({"family":"low","seed":19025},{"family":"low_grip","seed":19024},
                          {"seed":207400},{"family":"low","pattern":"recovery"}):
            with self.assertRaises(ValueError): self.reset(**selection)
            self.assertEqual(s.run_id,identity); self.assertEqual(s.run.decisions,0)

    def test_pause_stale_requests_and_reset_do_not_run_a_background_clock(self):
        s = self.session; first = self.reset(); playing = s.play({"run_id":s.run_id,"after":0})
        s.pause({"run_id":s.run_id})
        with self.assertRaises(ValueError): s.step({"run_id":s.run_id,"after":0,"automatic":True,"playback_epoch":playing["playback"]["epoch"]})
        self.assertEqual(s.run.decisions,0); second = self.reset()
        self.assertNotEqual(first["run_id"],second["run_id"])
        with self.assertRaises(ValueError): s.step({"run_id":first["run_id"],"after":0})
        with self.assertRaises(ValueError): s.step({"run_id":s.run_id,"after":False})

    def test_http_guards_without_a_socket(self):
        s = self.session; self.reset()
        def request(path,body=None,host="127.0.0.1:8096",origin="http://127.0.0.1:8096"):
            handler = Handler.__new__(Handler); result = []; raw = json.dumps(body or {}).encode()
            handler.path = path; handler.server = SimpleNamespace(server_port=8096,session=s)
            handler.rfile = io.BytesIO(raw); handler.headers = {"Host":host,"Origin":origin,"Content-Type":"application/json","Content-Length":str(len(raw))}
            handler.json = lambda status,value:result.append((status,value))
            (handler.do_GET if body is None else handler.do_POST)(); return result[0]
        self.assertEqual(request("/api/info")[0],200)
        self.assertEqual(request("/api/export")[1]["outcome"]["decisions"],0)
        self.assertEqual(request("/api/info",host="example.com")[0],403)
        self.assertEqual(request("/api/step",{"run_id":s.run_id,"after":0},origin="https://example.com")[0],403)
        self.assertEqual(request("/training/kessel_lab/harvest_runtime.py")[0],404)
