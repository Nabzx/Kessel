import copy
import io
import json
from types import SimpleNamespace
import unittest

from kessel_lab.bootstrap_runtime import REPORT, SOURCES, Handler, Session, verify_qualification


class QualifiedRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.session = Session()

    def reset(self, family="healthy", source=SOURCES[0]):
        return self.session.reset({"family":family,"seed":19000,"source":source})

    def test_pause_invalidates_inflight_playback_and_never_advances_physics(self):
        s = self.session; first = self.reset()
        play = s.play({"run_id":first["run_id"],"after":0})
        with self.assertRaises(ValueError): s.step({"run_id":s.run_id,"after":0,"steps":1})
        paused = s.pause({"run_id":s.run_id})
        self.assertEqual(paused["outcome"]["decisions"],0)
        with self.assertRaises(ValueError):
            s.step({"run_id":s.run_id,"after":0,"automatic":True,"playback_epoch":play["playback"]["epoch"]})
        stepped = s.step({"run_id":s.run_id,"after":0,"steps":2})
        self.assertEqual(stepped["outcome"]["decisions"],2)
        self.assertEqual(stepped["telemetry"]["owner"],"neural_policy")
        self.assertIsNotNone(stepped["telemetry"]["neural_proposal"])

    def test_reset_replaces_tokens_and_export_is_a_nonmutating_complete_snapshot(self):
        s = self.session; first = self.reset(); s.step({"run_id":s.run_id,"after":0,"steps":2})
        exported = s.export_trace(); json.dumps(exported,allow_nan=False)
        self.assertEqual(len(exported["frames"]),3); self.assertFalse(exported["applied_machine_commands"])
        self.assertEqual(exported["method"],"bootstrapped_motion_hold")
        self.assertEqual(exported["frames"][0]["supervision"]["applied_action"],exported["frames"][0]["action"])
        exported["frames"][0]["state"][0] = 999
        self.assertNotEqual(s.run.base.records[0]["state"][0],999)
        self.assertEqual(s.run.base.decisions,2)
        second = self.reset()
        self.assertNotEqual(first["run_id"],second["run_id"])
        self.assertEqual(first["frames"],second["frames"])
        with self.assertRaises(ValueError): s.step({"run_id":first["run_id"],"after":0})

    def test_invalid_selection_and_bounds_preserve_the_current_run(self):
        s = self.session; self.reset(); identity = s.run_id
        for body in ({"family":"healthy","source":SOURCES[0],"seed":208701},
                     {"family":"recovery","source":"phase_memory-7","seed":19000},
                     {"family":"receiver_far","source":SOURCES[0],"seed":19000}):
            with self.assertRaises(ValueError): s.reset(body)
            self.assertEqual(s.run_id,identity)
        for body in ({"after":False},{"after":0,"steps":11},{"after":0,"steps":True}):
            with self.assertRaises(ValueError): s.step({"run_id":s.run_id,**body})
        baseline = self.reset(source="phase_memory-19")
        self.assertEqual(baseline["method"],"original")
        self.assertFalse(baseline["playback"]["running"])

    def test_evidence_flags_cannot_replace_complete_per_seed_source_and_replay_checks(self):
        report = json.loads(REPORT.read_text())
        for mutate in (lambda r:r.update(admitted=False),lambda r:r.update(physics_replay_cases=0),
                       lambda r:r.update(healthy_exact=False),lambda r:r["plan"]["files"].pop("training/kessel_lab/runtime.py")):
            bad = copy.deepcopy(report); mutate(bad)
            with self.assertRaises(ValueError): verify_qualification(bad)

    def test_handler_guards_and_controls_work_without_a_listening_server(self):
        s = self.session; self.reset()
        def request(path,body=None,origin="http://127.0.0.1:8095",host="127.0.0.1:8095",content_type="application/json"):
            h = Handler.__new__(Handler); result = []
            h.path = path; h.server = SimpleNamespace(server_port=8095,session=s)
            raw = json.dumps(body or {}).encode(); h.rfile = io.BytesIO(raw)
            h.headers = {"Host":host,"Origin":origin,"Content-Type":content_type,"Content-Length":str(len(raw))}
            h.json = lambda status,value:result.append((status,value))
            (h.do_GET if body is None else h.do_POST)()
            return result[0]
        self.assertEqual(request("/api/info")[0],200)
        self.assertEqual(request("/api/play",{"run_id":s.run_id,"after":0})[0],200)
        self.assertEqual(request("/api/pause",{"run_id":s.run_id})[0],200)
        self.assertEqual(request("/api/export")[1]["outcome"]["decisions"],0)
        self.assertEqual(request("/api/step",{"run_id":s.run_id,"after":0},origin="https://example.com")[0],403)
        self.assertEqual(request("/api/info",host="example.com")[0],403)
        self.assertEqual(request("/api/reset",{},content_type="text/plain")[0],415)
        self.assertEqual(request("/training/kessel_lab/bootstrap_runtime.py")[0],404)


if __name__ == "__main__": unittest.main()
