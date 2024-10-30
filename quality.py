# from mip import *
# iron = Integer('iron')


from z3 import *
import time
from dataclasses import dataclass

# s = Solver()
s = Optimize()

resources = {}
for resource in ["iron", "copper"]:
    resources[resource] = Real(resource)
original_resources = resources.copy()

@dataclass
class Machine:
    name : str
    module_slots : int
    productivity : float = 0
    speed : float = 1

@dataclass
class Recipe:
    machine : Machine
    inputs: dict[str, int]
    outputs: dict[str, int]
    name: str | None = None
    accepts_productivity : bool = True
    
assembler = Machine(
    "Assembler", 
    module_slots=4, 
    speed=1.25
)

recipes = [
    Recipe(
        name="Copper Wire",
        machine=assembler,
        inputs={"copper": 1},
        outputs={"copper_wire": 2}
    ),
    Recipe(
        name="Iron Plates",
        machine=assembler,
        inputs={"iron": 1},
        outputs={"iron_plates": 1}
    ),
    Recipe(
        name="Green Circuits",
        machine=assembler,
        inputs={"copper_wire": 3, "iron_plates": 1},
        outputs={"green_circuits": 1}
    )
]

recipe_amounts = {}

all_resources = set()
all_resources.update(resources.keys())
for recipe in recipes:
    for resource in recipe.inputs.keys() | recipe.outputs.keys():
        all_resources.add(resource)

# init products
for resource in all_resources:
    if resource not in resources:
        resources[resource] = 0

for ri, recipe in enumerate(recipes):
    recipe_amounts[ri] = Real(f"recipe_{ri}")
    for resource, amount in recipe.inputs.items():
        resources[resource] -= recipe_amounts[ri] * amount
    for resource, amount in recipe.outputs.items():
        resources[resource] += recipe_amounts[ri] * amount

# no resource can be negative
for resource in resources:
    s.add(resources[resource] >= 0)

# we want green circuits
s.add(resources["green_circuits"] >= 1)
s.minimize(sum(original_resources.values()))

print("Solving...")
t0 = time.time()
res = s.check()
t1 = time.time()
print(f"Optimization took {t1-t0:.2f} seconds")

if res == sat:
    print("Solution found")
    print()
    m = s.model()
    print(f"Producing {m.evaluate(resources['green_circuits'])} green circuits")
    for ri, recipe in enumerate(recipes):
        print(f"Recipe {recipe.name} crafted in assembler: {m[recipe_amounts[ri]]}")
else:
    print("No solution found")
