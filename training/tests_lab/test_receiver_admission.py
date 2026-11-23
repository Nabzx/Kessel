import unittest
from kessel_lab.receiver_qualification import admitted
from kessel_lab.receiver_frame import METHOD


class AdmissionTests(unittest.TestCase):
    def cases(self):
        return [{"method":METHOD,"source":"phase_memory-"+str(seed),"family":family,
                 "full_success":True,"collision":False} for seed in (7,19,41)
                for family in ("nominal","receiver_far") for _ in range(8)]

    def test_incomplete_or_missing_cases_cannot_admit(self):
        cases=self.cases()
        self.assertTrue(admitted(cases,True))
        self.assertFalse(admitted(cases,False))
        self.assertFalse(admitted(cases[:-1],True))

    def test_each_seed_and_family_must_pass_without_collision(self):
        cases=self.cases();cases[0]["full_success"]=False
        self.assertTrue(admitted(cases,True))
        cases[1]["full_success"]=False
        self.assertFalse(admitted(cases,True))
        cases=self.cases();cases[0]["collision"]=True
        self.assertFalse(admitted(cases,True))


if __name__=="__main__":
    unittest.main()
