import json
import pandas as pd
import numpy as np
import gurobipy as gp
from gurobipy import GRB

# Load data
with open("data/portfolio-example.json", "r") as f:
    data = json.load(f)

# Extract data from the JSON
n = data["num_assets"]
sigma = np.array(data["covariance"])
mu = np.array(data["expected_return"])
mu_0 = data["target_return"]
k = data["portfolio_max_size"]

# Initialize the model
with gp.Model("portfolio") as model:
    # Decision variables
    x = model.addVars(n, lb=0, ub=1, name="x")  # Fraction of portfolio invested in each asset
    y = model.addVars(n, vtype=GRB.BINARY, name="y")  # Binary variables for whether an asset is selected
    
    # Objective: Minimize risk (variance)
    obj = gp.quicksum(
        sigma[i][j] * x[i] * x[j] for i in range(n) for j in range(n)
    )
    model.setObjective(obj, GRB.MINIMIZE)

    # Constraint 1: Total expected return must exceed the target return
    model.addConstr(
        gp.quicksum(mu[i] * x[i] for i in range(n)) >= mu_0,
        name="return"
    )

    # Constraint 2: Invest in at most k assets
    model.addConstr(
        gp.quicksum(y[i] for i in range(n)) <= k,
        name="max_assets"
    )

    # Constraint 3: Only invest in an asset if it is selected
    model.addConstrs(
        (x[i] <= y[i] for i in range(n)), 
        name="selection"
    )

    # Constraint 4: Total investment across all assets must equal 1
    model.addConstr(
        gp.quicksum(x[i] for i in range(n)) == 1,
        name="budget"
    )

    # Optimize the model
    model.optimize()

    # Write the solution into a DataFrame
    if model.Status == GRB.OPTIMAL:
        portfolio = [var.X for var in model.getVars() if "x" in var.VarName]
        risk = model.ObjVal
        expected_return = sum(mu[i] * portfolio[i] for i in range(n))
        
        df = pd.DataFrame(
            data=portfolio + [risk, expected_return],
            index=[f"asset_{i}" for i in range(n)] + ["risk", "return"],
            columns=["Portfolio"],
        )
        print(df)
    else:
        print("No optimal solution found.")
