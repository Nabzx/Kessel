from types import SimpleNamespace
import unittest

import numpy as np

from kessel_lab.forecast_assistance import AssistanceController, CountedPredictor
from kessel_lab.harvest_scenarios import environment
from kessel_lab.study_tools import Budget


class Actor:
    def __init__(self,override=False): self.task = SimpleNamespace(mode="collect"); self.memory = None; self.override = override
    def act(self,*args):
        self.last = {"override":self.override,"proposal_source":"learned_linear_feedback"}
        return np.array([[.2,0,.2,.1]])


class CandidateModel:
    def __init__(self): self.calls = 0
    def predict(self,state,actions):
        self.calls += len(actions); following = state.copy()
        gain = (actions[:,0] > .3)*10.
        following[:,7] += gain; following[:,15:79] -= gain[:,None]/(state[:,None,81]*.25*64)
        return {"next_state":following,"reward":np.zeros(len(state)),"events":np.zeros((len(state),4)),"disagreement":np.zeros(len(state))}


class ForecastAssistanceTests(unittest.TestCase):
    def test_independent_guard_bypasses_all_candidate_queries(self):
        env,_ = environment("nominal",19020); model = CandidateModel(); budget = Budget(5,model_rows=5)
        controller = AssistanceController(Actor(True),env,CountedPredictor(model,budget),1,True)
        np.testing.assert_array_equal(controller.act(None,None),[[.2,0,.2,.1]])
        self.assertEqual(model.calls,0)

    def test_shadow_spends_the_same_candidate_budget_without_changing_actions(self):
        env,_ = environment("nominal",19020)
        results = []
        for enabled in (False,True):
            budget = Budget(5,model_rows=5); model = CandidateModel(); predictor = CountedPredictor(model,budget)
            controller = AssistanceController(Actor(),env,predictor,1,enabled); action = controller.act(None,None)
            state = np.repeat(controller.last["assistance"]["predictions"]["next_state"][:1],1,axis=0)
            from kessel_training.wm_state import pack
            predictor.predict(pack(env),action)
            self.assertEqual(model.calls,5); self.assertEqual(predictor.cache_hits,1)
            results.append(action)
        self.assertEqual(results[0][0,0],.2); self.assertAlmostEqual(results[1][0,0],.35)
