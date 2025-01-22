import gurobipy as gp
from gurobipy import GRB
import numpy as np

# 24 Hour Load Forecast (MW)
load_forecast = [
    4,
    4,
    4,
    4,
    4,
    4,
    6,
    6,
    12,
    12,
    12,
    12,
    12,
    4,
    4,
    4,
    4,
    16,
    16,
    16,
    16,
    6.5,
    6.5,
    6.5,
]

# solar energy forecast (MW)
solar_forecast = [
    0,
    0,
    0,
    0,
    0,
    0,
    0.5,
    1.0,
    1.5,
    2.0,
    2.5,
    3.5,
    3.5,
    2.5,
    2.0,
    1.5,
    1.0,
    0.5,
    0,
    0,
    0,
    0,
    0,
    0,
]

# thermal units
thermal_units = ["gen1", "gen2", "gen3"]

# global number of time intervals
nTimeIntervals = len(load_forecast)
nThermalUnits = len(thermal_units)

# thermal units' costs  (a + b*p + c*p^2), (startup and shutdown costs)
thermal_units_cost, a, b, c, sup_cost, sdn_cost = gp.multidict(
    {
        "gen1": [5.0, 0.5, 1.0, 2, 1],
        "gen2": [5.0, 0.5, 0.5, 2, 1],
        "gen3": [5.0, 3.0, 2.0, 2, 1],
    }
)

# thernal units operating limits
thermal_units_limits, pmin, pmax = gp.multidict(
    {"gen1": [1.5, 5.0], "gen2": [2.5, 10.0], "gen3": [1.0, 3.0]}
)

# thermal units dynamic data (initial commitment status)
thermal_units_dyn_data, init_status = gp.multidict(
    {"gen1": [0], "gen2": [0], "gen3": [0]}
)

# Map thermal units to indices for matrix operations
unit_indices = {unit: i for i, unit in enumerate(thermal_units)}

# Convert parameters to numpy arrays for vectorized operations
a_arr = np.array([a[g] for g in thermal_units])
b_arr = np.array([b[g] for g in thermal_units])
c_arr = np.array([c[g] for g in thermal_units])
sup_cost_arr = np.array([sup_cost[g] for g in thermal_units])
sdn_cost_arr = np.array([sdn_cost[g] for g in thermal_units])
pmin_arr = np.array([pmin[g] for g in thermal_units])
pmax_arr = np.array([pmax[g] for g in thermal_units])
init_status_arr = np.array([init_status[g] for g in thermal_units])

def show_results():
    obj_val_s = model.ObjVal
    print(f" OverAll Cost = {round(obj_val_s, 2)}\n")
    print("%5s" % "time", end=" ")
    for t in range(nTimeIntervals):
        print("%4s" % t, end=" ")
    print("\n")

    for g, g_name in enumerate(thermal_units):
        print("%5s" % g_name, end=" ")
        for t in range(nTimeIntervals):
            # Use integer indexing into MVar
            print("%4.1f" % thermal_units_out_power[g, t].X, end=" ")
        print("\n")

    print("%5s" % "Solar", end=" ")
    for t in range(nTimeIntervals):
        print("%4.1f" % solar_forecast[t], end=" ")
    print("\n")

    print("%5s" % "Load", end=" ")
    for t in range(nTimeIntervals):
        print("%4.1f" % load_forecast[t], end=" ")
    print("\n")



with gp.Env() as env, gp.Model(env=env) as model:
     # Create variables using addMVar
    thermal_units_out_power = model.addMVar(
        (nThermalUnits, nTimeIntervals), lb=0, name="thermal_units_out_power"
    )
    thermal_units_startup_status = model.addMVar(
        (nThermalUnits, nTimeIntervals), vtype=GRB.BINARY, name="startup_status"
    )
    thermal_units_shutdown_status = model.addMVar(
        (nThermalUnits, nTimeIntervals), vtype=GRB.BINARY, name="shutdown_status"
    )
    thermal_units_comm_status = model.addMVar(
        (nThermalUnits, nTimeIntervals), vtype=GRB.BINARY, name="commitment_status"
    )

        # Define objective function
    power_terms = c_arr[:, None] * thermal_units_out_power * thermal_units_out_power
    linear_terms = b_arr[:, None] * thermal_units_out_power
    fixed_terms = a_arr[:, None] * thermal_units_comm_status
    startup_terms = sup_cost_arr[:, None] * thermal_units_startup_status
    shutdown_terms = sdn_cost_arr[:, None] * thermal_units_shutdown_status

    obj_fun_expr = (
    gp.quicksum(power_terms[g, t] for g in range(nThermalUnits) for t in range(nTimeIntervals))
    + gp.quicksum(linear_terms[g, t] for g in range(nThermalUnits) for t in range(nTimeIntervals))
    + gp.quicksum(fixed_terms[g, t] for g in range(nThermalUnits) for t in range(nTimeIntervals))
    + gp.quicksum(startup_terms[g, t] for g in range(nThermalUnits) for t in range(nTimeIntervals))
    + gp.quicksum(shutdown_terms[g, t] for g in range(nThermalUnits) for t in range(nTimeIntervals))
    )


    model.setObjective(obj_fun_expr, GRB.MINIMIZE)

    # Power balance constraints
    power_sum = thermal_units_out_power.sum(axis=0)
    solar_forecast_arr = np.array(solar_forecast)
    load_forecast_arr = np.array(load_forecast)
    model.addConstr(power_sum + solar_forecast_arr == load_forecast_arr, name="power_balance")

    # Logical constraints
    comm_status_diff = thermal_units_comm_status[:, 1:] - thermal_units_comm_status[:, :-1]
    model.addConstr(
        comm_status_diff
        == thermal_units_startup_status[:, 1:] - thermal_units_shutdown_status[:, 1:],
        name="logical_status_diff",
    )

    model.addConstr(
        thermal_units_startup_status + thermal_units_shutdown_status <= 1,
        name="no_simultaneous_startup_shutdown",
    )

    # Initial commitment status
    model.addConstr(
        thermal_units_comm_status[:, 0] - init_status_arr
        == thermal_units_startup_status[:, 0] - thermal_units_shutdown_status[:, 0],
        name="initial_status",
    )

    # Physical constraints with indicators
    for g in range(nThermalUnits):
        for t in range(nTimeIntervals):
            model.addGenConstrIndicator(
                thermal_units_comm_status[g, t],
                True,
                thermal_units_out_power[g, t] >= pmin_arr[g],
                name=f"min_power_{g}_{t}",
            )
            model.addGenConstrIndicator(
                thermal_units_comm_status[g, t],
                True,
                thermal_units_out_power[g, t] <= pmax_arr[g],
                name=f"max_power_{g}_{t}",
            )
            model.addGenConstrIndicator(
                thermal_units_comm_status[g, t],
                False,
                thermal_units_out_power[g, t] == 0,
                name=f"zero_power_{g}_{t}",
            )

    # Optimize model
    model.optimize()

    # Show results
    show_results()
