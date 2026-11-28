"""Experimental one-step candidate refinement; guards always retain precedence."""
import copy

import numpy as np

from kessel_training.wm_state import pack, violations


class CountedPredictor:
    def __init__(self,model,budget): self.model = model; self.budget = budget; self.rows = 0; self.cache = None; self.cache_hits = 0
    def predict(self,states,actions):
        if len(actions) == 1 and self.cache is not None:
            old_states,old_actions,old = self.cache
            for index,(state,action) in enumerate(zip(old_states,old_actions)):
                if np.array_equal(state,states[0]) and np.array_equal(action,actions[0]):
                    self.cache_hits += 1
                    return {name:value[index:index+1].copy() if isinstance(value,np.ndarray) else value for name,value in old.items()}
        self.budget.charge("model_rows",len(actions)); self.rows += len(actions)
        result = self.model.predict(states,actions)
        self.cache = (states.copy(),actions.copy(),result) if len(actions) == 5 else None
        return result


class AssistanceController:
    def __init__(self,actor,env,predictor,threshold,enabled):
        self.actor = actor; self.env = env; self.predictor = predictor; self.threshold = threshold; self.enabled = enabled
        self.last = None; self.changed = 0
    @property
    def task(self): return self.actor.task
    @property
    def memory(self): return self.actor.memory

    def act(self,observation,packet):
        base = self.actor.act(observation,packet); self.last = copy.deepcopy(self.actor.last)
        if self.last["override"]:
            self.last["assistance"] = {"mode":"independent_guard","model_rows":0,"selected":0}; return base
        actions = np.repeat(base,5,axis=0)
        actions[1,0] += .15; actions[2,0] -= .15; actions[3,3] += .15; actions[4,3] -= .15
        actions = np.clip(actions,-1,1); states = np.repeat(pack(self.env),5,axis=0)
        predicted = self.predictor.predict(states,actions); following = predicted["next_state"]
        validity = violations(following)
        invalid = np.zeros(5,dtype=bool)
        for name,values in validity.items(): invalid |= abs(values) > 25 if name == "mass_error_kg" else values
        accepted = ~invalid & (predicted["disagreement"] <= self.threshold) & (predicted["events"][:,3] < .5)
        scores = following[:,7]-states[:,7]+2*(following[:,8]-states[:,8])-5*(following[:,9]-states[:,9])-.0001*(following[:,12]-states[:,12])
        ranked = np.where(accepted,scores,-np.inf); best = int(np.argmax(ranked))
        change = bool(self.enabled and self.task.mode in ("collect","sweep","back_out") and accepted[0] and accepted[best] and scores[best] > scores[0]+5)
        selected = best if change else 0; chosen = actions[selected:selected+1].copy(); self.changed += selected != 0
        self.last.update(applied_action=chosen[0].tolist(),application_source="privileged_hybrid_refinement" if selected else self.last["proposal_source"])
        self.last["assistance"] = {"mode":"candidate_refinement" if self.enabled else "shadow_only","model_rows":5,"selected":selected,"best":best,
            "candidate_actions":actions.tolist(),"accepted":accepted.tolist(),"scores":scores.tolist(),"threshold":self.threshold,
            "predictions":{name:value.tolist() for name,value in predicted.items() if name in ("next_state","reward","events","disagreement")},
            "base_proposal":base[0].tolist(),"eligible_mode":self.task.mode in ("collect","sweep","back_out")}
        return chosen
