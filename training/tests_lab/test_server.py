import unittest
from kessel_lab.server import Session

class SessionTests(unittest.TestCase):
    def test_reset_stale_counter_and_terminal(self):
        s=Session();first=s.reset({'family':'nominal','seed':19000,'source':'phase_memory-7'})
        self.assertEqual(first['frames'][0]['state'][7],0)
        step=s.step({'run_id':first['run_id'],'after':0,'steps':2})
        self.assertEqual(step['outcome']['decisions'],2)
        with self.assertRaises(ValueError):s.step({'run_id':first['run_id'],'after':0})
        second=s.reset({'family':'nominal','seed':19000,'source':'phase_memory-7'})
        self.assertNotEqual(first['run_id'],second['run_id'])
        self.assertEqual(first['frames'],second['frames'])
        with self.assertRaises(ValueError):s.step({'run_id':first['run_id'],'after':0})
    def test_test_split_and_unbounded_batches_rejected(self):
        s=Session()
        with self.assertRaises(ValueError):s.reset({'family':'nominal','seed':206200,'source':'phase_memory-7'})
        first=s.reset({'family':'nominal','seed':19000,'source':'phase_memory-7'})
        with self.assertRaises(ValueError):s.step({'run_id':first['run_id'],'after':0,'steps':11})
        self.assertEqual(s.run.decisions,0)

if __name__=='__main__':unittest.main()
