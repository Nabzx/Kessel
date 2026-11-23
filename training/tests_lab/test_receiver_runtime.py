import unittest
from kessel_lab.receiver_runtime import verify_qualification


class RuntimeAdmissionTests(unittest.TestCase):
    def test_an_admitted_flag_cannot_replace_seed_family_evidence(self):
        for report in ({"admitted":False},{"admitted":True,"complete":True,"cases":[]}):
            with self.assertRaises(ValueError):verify_qualification(report)


class QualifiedSessionTests(unittest.TestCase):
    def test_qualified_reset_step_and_source_identity_without_network(self):
        from kessel_lab.receiver_runtime import Session
        s=Session()
        reset=s.reset({"family":"receiver_far","seed":19000,"source":"receiver_x_frame-7"})
        self.assertEqual(reset["source"],"receiver_x_frame-7")
        self.assertIn("receiver-frame",reset["control_description"])
        self.assertEqual(reset["frames"][0]["state"][7],0)
        self.assertIsNotNone(reset["adapter_sha256"])
        stepped=s.step({"run_id":reset["run_id"],"after":0,"steps":2})
        self.assertEqual(stepped["outcome"]["decisions"],2)
        self.assertEqual(stepped["qualification_sha256"],reset["qualification_sha256"])
        with self.assertRaises(ValueError):
            s.reset({"family":"low","seed":19000,"source":"receiver_x_frame-7"})
        with self.assertRaises(ValueError):
            s.reset({"family":"nominal","seed":205800,"source":"receiver_x_frame-7"})
        reference=s.reset({"family":"nominal","seed":19000,"source":"reference"})
        self.assertIsNone(reference["adapter_sha256"])
        self.assertEqual(reference["control_description"],"Conventional reference")


if __name__=="__main__":
    unittest.main()
