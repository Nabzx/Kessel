"""Privileged initial-state certificate, never an input to task control."""
import numpy as np


def certificate(state):
    state = np.asarray(state,dtype=float)
    if state.shape != (102,) or not np.isfinite(state).all() or state[10] != 0 or state[7] != 0:
        raise ValueError("finite empty initial state required")
    blade_floor = .35+2*np.sin(-.1)
    available = float(np.maximum(state[15:79]-blade_floor,0).sum()*.25*state[81])
    mass = 10500.; grip = state[83]*mass*9.81*np.cos(state[84])
    margin = float(min(22000.,grip)-mass*9.81*np.sin(state[84])*np.cos(state[2])-.02*mass*9.81*np.cos(state[84]))
    reasons = []
    if available < 3200: reasons.append("recoverable_material_below_3200_kg")
    if margin < 200: reasons.append("empty_forward_margin_below_200_n")
    return {"kind":"privileged_synthetic_initial_feasibility_v1","supported":not reasons,"reasons":reasons,
            "available_above_blade_kg":available,"empty_forward_margin_n":margin,
            "minimum_available_kg":3200.,"minimum_forward_margin_n":200.,"controller_input":False}


def summary(cases,fresh=False):
    result = []; keys = sorted({(c["source"],c["family"],c["pattern"]) for c in cases if c["split"] not in ("known_regression","start_guard_challenge")},key=str)
    for source,family,pattern in keys:
        rows = [c for c in cases if c["split"] not in ("known_regression","start_guard_challenge") and (c["source"],c["family"],c["pattern"]) == (source,family,pattern)]
        admitted = [c for c in rows if c["evaluation"]["criterion"] == "stop" or c["certificate"]["supported"]]
        result.append({"source":source,"family":family,"pattern":pattern,"scheduled":len(rows),"supported":len(admitted),
                       "supported_passed":sum(c["evaluation"]["passed"] for c in admitted),"original_passed":sum(c["evaluation"]["passed"] for c in rows),
                       "proposed_refusals_passed":sum(bool(c["evaluation"].get("proposed_refusal",{} ) and c["evaluation"]["proposed_refusal"]["passed"]) for c in rows),
                       "passed":bool(len(admitted) >= (8 if fresh else 0) and all(c["evaluation"]["passed"] for c in admitted))})
    return result
