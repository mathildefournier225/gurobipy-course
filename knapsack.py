import numpy as np
import gurobipy as gp
from gurobipy import GRB

def generate_knapsack(num_items):
    # Fix seed value
    rng = np.random.default_rng(seed=0)
    # Item values, weights
    values = rng.uniform(low=1, high=25, size=num_items)
    weights = rng.uniform(low=5, high=100, size=num_items)
    # Knapsack capacity
    capacity = 0.7 * weights.sum()

    return values, weights, capacity


def solve_knapsack_model(values, weights, capacity):
    num_items = len(values)
    
    # Convert values and weights to dicts
    value_dict = {i: values[i] for i in range(num_items)}
    weight_dict = {i: weights[i] for i in range(num_items)}
    
    with gp.Env() as env:
        with gp.Model(name="knapsack", env=env) as model:
            # Define decision variables (binary: 0 or 1)
            x = model.addVars(num_items, vtype=GRB.BINARY, name="x")
            
            # Define the objective function (maximize total value)
            model.setObjective(gp.quicksum(value_dict[i] * x[i] for i in range(num_items)), GRB.MAXIMIZE)
            
            # Define the constraint (capacity constraint)
            model.addConstr(gp.quicksum(weight_dict[i] * x[i] for i in range(num_items)) <= capacity, "Capacity")
            
            # Optimize the model
            model.optimize()
            
            # Check if a feasible solution exists
            if model.status == GRB.OPTIMAL:
                print("Optimal solution found.")
                # Retrieve the solution
                selected_items = [i for i in range(num_items) if x[i].x > 0.5]
                total_value = model.objVal
                total_weight = sum(weight_dict[i] for i in selected_items)
                print(f"Selected items: {selected_items}")
                print(f"Total value: {total_value}")
                print(f"Total weight: {total_weight}")
            else:
                print("No optimal solution found.")

# Example usage
data = generate_knapsack(10000)
solve_knapsack_model(*data)


