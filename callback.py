from functools import partial

import gurobipy as gp
from gurobipy import GRB


class CallbackData:
    def __init__(self):
        self.last_gap_change_time = -GRB.INFINITY
        self.last_gap = GRB.INFINITY


def callback(model, where, *, cbdata):
    if where != GRB.Callback.MIP:
        return
    if model.cbGet(GRB.Callback.MIP_SOLCNT) == 0:
        return

    # Use model.terminate() to end the search when required...
    if model.terminate():
        return
    
    # Obtenir l'écart actuel et le temps d'exécution
    current_gap = model.cbGet(GRB.Callback.MIP_GAP)
    current_time = model.cbGet(GRB.Callback.RUNTIME)

    # Vérifier si l'écart a changé de manière significative
    if abs(current_gap - cbdata.last_gap) > epsilon_to_compare_gap:
        cbdata.last_gap = current_gap
        cbdata.last_gap_change_time = current_time
        print(f"[INFO] Nouveau gap: {current_gap:.6f} à {current_time:.2f} secondes")
    # Vérifier si l'optimisation doit être arrêtée
    elif current_time - cbdata.last_gap_change_time > time_from_best:
        print("[STOP] Temps écoulé sans amélioration significative du gap.")
        model.terminate()



with gp.read("data/mkp.mps/mkp.mps") as model:
    # Global variables used in the callback function
    time_from_best = 15
    epsilon_to_compare_gap = 1e-4

    # Initialize data passed to the callback function
    callback_data = CallbackData()
    callback_func = partial(callback, cbdata=callback_data)

    model.optimize(callback_func)

