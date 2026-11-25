import hashlib
import unittest
import numpy as np
from kessel_lab.reserve_bootstrap import inspect


class ReservationFingerprintTests(unittest.TestCase):
    def test_float32_equivalent_states_cannot_be_lost_by_the_prefilter(self):
        state = np.arange(102,dtype=np.float64)/1000+.1
        digest = hashlib.sha256(state.astype("<f4").tobytes()).hexdigest()
        altered = state.copy(); altered[15] += 1e-12
        markers = {float(np.float32(state[15]))}
        for value in ({"state":altered.tolist()},{"states":altered[None,:]}):
            self.assertTrue(inspect(value,{208700},{digest},markers))

    def test_seed_checks_run_even_when_no_pile_can_match(self):
        for value in ({"seed":208700},{"seed":"208700"},{"seeds":[1,208700]},{"seeds":np.array([208700])}):
            self.assertTrue(inspect(value,{208700},set(),set()))
        self.assertFalse(inspect({"seed":19000},{208700},set(),set()))

    def test_json_piles_and_nested_states_are_checked(self):
        pile = np.arange(64,dtype=float).reshape(8,8)+.2
        digest = hashlib.sha256(pile.astype("<f8").tobytes()).hexdigest()
        marker = {float(np.float32(pile.flat[0]))}
        self.assertTrue(inspect({"height":pile.tolist()},set(),{digest},marker))
        state = np.zeros(102); state[15:79] = pile.flatten()
        self.assertTrue(inspect({"frames":[{"next_state":state.tolist()}]},set(),{digest},marker))


if __name__ == "__main__": unittest.main()
