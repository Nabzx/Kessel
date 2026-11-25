import copy
import json
import unittest
from kessel_lab.bootstrap_qualification import METHOD, jobs, admitted, trace_identity


class FreshStoppingAdmissionTests(unittest.TestCase):
    def test_every_seed_and_family_must_pass_without_collision(self):
        rows = [{**j,"criterion_passed":True,"collision":False,"weights_unchanged":True} for j in jobs()]
        self.assertEqual(len(rows),120)
        self.assertTrue(admitted(rows,True,True))
        selected = [i for i,c in enumerate(rows) if c["method"] == METHOD and c["source"] == "phase_memory-7" and c["pattern"] == "recovery"]
        rows[selected[0]]["criterion_passed"] = False
        self.assertTrue(admitted(rows,True,True))
        rows[selected[1]]["criterion_passed"] = False
        self.assertFalse(admitted(rows,True,True))
        rows[selected[1]]["criterion_passed"] = True; rows[selected[0]]["collision"] = True
        self.assertFalse(admitted(rows,True,True))

    def test_incomplete_unmatched_or_duplicate_data_never_admits(self):
        rows = [{**j,"criterion_passed":True,"collision":False,"weights_unchanged":True} for j in jobs()]
        self.assertFalse(admitted(rows,False,True)); self.assertFalse(admitted(rows,True,False))
        missing = rows[1:]; self.assertFalse(admitted(missing,True,True))
        self.assertFalse(admitted(rows[:-1],True,True))
        duplicate = copy.deepcopy(rows); duplicate[12]["seed"] = duplicate[0]["seed"]
        self.assertFalse(admitted(duplicate,True,True))
        wrong = copy.deepcopy(rows); wrong[0]["seed"] = 1
        self.assertFalse(admitted(wrong,True,True))

    def test_practice_journal_and_identity_survive_source_hash_values(self):
        from kessel_lab.bootstrap_hold_pilot import make_run
        job = {"method":METHOD,"source":"phase_memory-7","seed":19000,"kind":"task","pattern":"healthy","criterion":"delivery"}
        run = make_run(job); obs = run.env.observe(); action = run.actor.act(obs)
        payload = {"identity":trace_identity(job,run.scenario,{"source":"some hash"}),
                   "job":job,"observation":{k:v.tolist() for k,v in obs.items()},
                   "supervision":run.actor.last,"action":action.tolist()}
        json.dumps(payload,allow_nan=False)
        self.assertEqual(len(payload["identity"]),64)
        self.assertNotEqual(payload["identity"],trace_identity(job,run.scenario,{"source":"different hash"}))


if __name__ == "__main__": unittest.main()
