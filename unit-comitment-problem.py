import gurobipy as gp
from gurobipy import GRB

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

# global number of time intervals
nTimeIntervals = len(load_forecast)

# thermal units
thermal_units = ["gen1", "gen2", "gen3"]

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


def show_results():
    obj_val_s = model.ObjVal
    print(f" OverAll Cost = {round(obj_val_s, 2)}	")
    print("\n")
    print("%5s" % "time", end=" ")
    for t in range(nTimeIntervals):
        print("%4s" % t, end=" ")
    print("\n")

    for g in thermal_units:
        print("%5s" % g, end=" ")
        for t in range(nTimeIntervals):
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
    # Add variables for thermal units
    thermal_units_out_power = model.addVars(
        thermal_units, range(nTimeIntervals), lb=0, name="thermal_units_out_power"
    )
    thermal_units_startup_status = model.addVars(
        thermal_units, range(nTimeIntervals), vtype=GRB.BINARY, name="startup_status"
    )
    thermal_units_shutdown_status = model.addVars(
        thermal_units, range(nTimeIntervals), vtype=GRB.BINARY, name="shutdown_status"
    )
    thermal_units_comm_status = model.addVars(
        thermal_units, range(nTimeIntervals), vtype=GRB.BINARY, name="commitment_status"
    )

    # Define objective function
    obj_fun_expr = gp.QuadExpr()
    for t in range(nTimeIntervals):
        for g in thermal_units:
            p = thermal_units_out_power[g, t]
            u = thermal_units_comm_status[g, t]
            v = thermal_units_startup_status[g, t]
            w = thermal_units_shutdown_status[g, t]
            obj_fun_expr += (
                a[g] * u + b[g] * p + c[g] * p * p + sup_cost[g] * v + sdn_cost[g] * w
            )
    model.setObjective(obj_fun_expr, GRB.MINIMIZE)

    # Power balance equations
    for t in range(nTimeIntervals):
        model.addConstr(
            gp.quicksum(thermal_units_out_power[g, t] for g in thermal_units)
            + solar_forecast[t]
            == load_forecast[t],
            name=f"power_balance_{t}",
        )

    # Thermal units logical constraints
    for t in range(nTimeIntervals):
        for g in thermal_units:
            if t == 0:
                model.addConstr(
                    thermal_units_comm_status[g, t] - init_status[g]
                    == thermal_units_startup_status[g, t]
                    - thermal_units_shutdown_status[g, t],
                    name=f"logical1_{g}_{t}",
                )
            else:
                model.addConstr(
                    thermal_units_comm_status[g, t]
                    - thermal_units_comm_status[g, t - 1]
                    == thermal_units_startup_status[g, t]
                    - thermal_units_shutdown_status[g, t],
                    name=f"logical1_{g}_{t}",
                )

            model.addConstr(
                thermal_units_startup_status[g, t]
                + thermal_units_shutdown_status[g, t]
                <= 1,
                name=f"logical2_{g}_{t}",
            )

    # Thermal units physical constraints
    for t in range(nTimeIntervals):
        for g in thermal_units:
            model.addGenConstrIndicator(
                thermal_units_comm_status[g, t],
                True,
                thermal_units_out_power[g, t] >= pmin[g],
                name=f"min_power_{g}_{t}",
            )
            model.addGenConstrIndicator(
                thermal_units_comm_status[g, t],
                True,
                thermal_units_out_power[g, t] <= pmax[g],
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
