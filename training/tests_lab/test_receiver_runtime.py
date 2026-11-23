import unittest
from kessel_lab.receiver_runtime import verify_qualification


class RuntimeAdmissionTests(unittest.TestCase):
    def test_an_admitted_flag_cannot_replace_seed_family_evidence(self):
        for report in ({"admitted":False},{"admitted":True,"complete":True,"cases":[]}):
            with self.assertRaises(ValueError):verify_qualification(report)


if __name__=="__main__":
    unittest.main()
