# from mip import *
# iron = Integer('iron')


from z3 import *
import time
from dataclasses import dataclass
from collections import defaultdict

# s = Solver()
s = Optimize()

# map from resource -> quality -> amount
# per default, all resources are zero
# only for normal (quality=0) resources, we want the amount to be a Real
resources = defaultdict(lambda: defaultdict(lambda: 0))
for resource in ["iron", "copper"]:
    resources[resource][0] = Real(resource)
# deep copy
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

# 0 = normal, 1 = uncommon, 2 = rare
max_quality = 2

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

recipe_amounts = defaultdict(lambda: {})

for ri, recipe in enumerate(recipes):
    for q in range(max_quality):
        recipe_amounts[ri][q] = Real(f"recipe_{ri}_q{q}")
        for resource, amount in recipe.inputs.items():
            resources[resource][q] -= recipe_amounts[ri][q] * amount
        for resource, amount in recipe.outputs.items():
            resources[resource][q] += recipe_amounts[ri][q] * amount

# no resource can be negative
for resource, quality_amounts in resources.items():
    for quality, amount in quality_amounts.items():
        s.add(amount >= 0)

# we want green circuits
goal_resource = resources["green_circuits"][0]
s.add(goal_resource >= 1)
s.minimize(sum(sum(quality_amounts.values()) for quality_amounts in original_resources.values()))

print("Solving...")
t0 = time.time()
res = s.check()
t1 = time.time()
print(f"Optimization took {t1-t0:.2f} seconds")

if res == sat:
    print("Solution found")
    print()
    m = s.model()
    print(f"Producing {m.evaluate(goal_resource)} green circuits")
    for ri, recipe in enumerate(recipes):
        print(f"{recipe.name} crafted in assembler: ")
        for q in range(max_quality):
            print(f"  Quality {q}: {m[recipe_amounts[ri][q]]}")
else:
    print("No solution found")
