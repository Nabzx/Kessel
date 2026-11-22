import unittest
import numpy as np
from kessel_lab.runtime import Run, environment

class RuntimeTests(unittest.TestCase):
    def test_learned_run_never_calls_teacher(self):
        from unittest.mock import patch
        with patch('kessel_training.controller.ReferenceController.act',side_effect=AssertionError('teacher')):
            run=Run('nominal',207600,'phase_memory-7')
            run.step()
            self.assertEqual(run.decisions,1)
            self.assertEqual(len(run.records[0]['action']),4)

    def test_shift_preserves_empty_start_and_changes_observation(self):
        base,_=environment('nominal',207600)
        shifted,_=environment('receiver_left',207600)
        self.assertEqual(float(shifted.payload[0]),0)
        self.assertAlmostEqual(shifted.observe()['proprio'][0,10]-base.observe()['proprio'][0,10],1)
        self.assertTrue(np.array_equal(base.pile.height,shifted.pile.height))

    def test_live_inputs_are_bounded(self):
        for args in [('unknown',1),('nominal',True),('nominal',-1),('nominal',210000)]:
            with self.assertRaises(ValueError): environment(*args)
        with self.assertRaises(ValueError): Run('nominal',207600,'not-a-checkpoint')

if __name__=='__main__': unittest.main()
