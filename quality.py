# from mip import *
# iron = Integer('iron')


from z3 import *
import time
from dataclasses import dataclass
from collections import defaultdict

# s = Solver()
s = Optimize()

# objective = "overhead"
objective = "inputs"
goal_item = "green_circuit"
goal_quality = 2

# map from resource -> quality -> amount
# per default, all resources are zero
# only for normal (quality=0) resources, we want the amount to be a Real
resources = defaultdict(lambda: defaultdict(lambda: 0))
inputs = defaultdict(lambda: defaultdict(lambda: 0))
for resource in ["iron_ore", "copper_ore"]:
    v = Real(resource)
    resources[resource][0] = v
    inputs[resource][0] = v
    
rarities = ["normal", "uncommon", "rare", "epic", "legendary"]
max_quality = 2

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
    accepts_quality : bool = True
    
def itemName(internal_name):
    # iron_ore => Iron Ore
    return " ".join([word.capitalize() for word in internal_name.split("_")])

def qualityName(quality, padding=True):
    max_len = max(len(r) for r in rarities)
    name = rarities[quality]
    if not padding:
        return name
    return " " * (max_len - len(name)) + name # + f" ({quality})"
    
# miner = Machine(
#     "Miner",
#     module_slots=3,
#     speed=1 # TODO: 
# )

smelter = Machine(
    "Smelter",
    module_slots=2,
    speed=2
)
    
assembler = Machine(
    "Assembler", 
    module_slots=4, 
    speed=1.25
)

recipes = [
    Recipe(
        name="Copper Smelting",
        machine=smelter,
        inputs={"copper_ore": 1},
        outputs={"copper_plate": 1}
    ),
    Recipe(
        name="Iron Smelting",
        machine=smelter,
        inputs={"iron_ore": 1},
        outputs={"iron_plate": 1}
    ),
    Recipe(
        name="Copper Wire",
        machine=assembler,
        inputs={"copper_plate": 1},
        outputs={"copper_wire": 2}
    ),
    Recipe(
        name="Green Circuits",
        machine=assembler,
        inputs={"copper_wire": 3, "iron_plate": 1},
        outputs={"green_circuit": 1}
    )
]

recipe_amounts = defaultdict(lambda: {})

for ri, recipe in enumerate(recipes):
    for q in range(max_quality+1):
        recipe_amounts[ri][q] = Real(f"recipe_{ri}_q{q}")
        for resource, amount in recipe.inputs.items():
            resources[resource][q] -= recipe_amounts[ri][q] * amount
        for resource, amount in recipe.outputs.items():
            # resources[resource][q] += recipe_amounts[ri][q] * amount
            
            # assuming 4 quality 3 => 10%
            percent_sum = 0
            percentage = 0.1
            for q2 in range(q+1,max_quality+1):
                percent_sum += percentage
                resources[resource][q2] += recipe_amounts[ri][q] * amount * percentage
                percentage /= 10
            resources[resource][q] += recipe_amounts[ri][q] * amount * (1-percent_sum)
            # quality modules
            # if q < max_quality:
            #     resources[resource][q+1] += recipe_amounts[ri][q] * amount * 0.1

# no resource can be negative
for resource, quality_amounts in resources.items():
    for quality, amount in quality_amounts.items():
        s.add(amount >= 0)
        
# no negative machines
for ri, recipe in enumerate(recipes):
    for q in range(max_quality+1):
        s.add(recipe_amounts[ri][q] >= 0)

goal_resource = resources[goal_item][goal_quality]
s.add(goal_resource >= 1)

org_objective =  objective
if objective == "inputs":
    objective = sum(sum(quality_amounts.values()) for quality_amounts in inputs.values())
elif objective == "overhead":
    objective = sum(sum(quality_amounts.values()) for quality_amounts in resources.values())
else:
    raise ValueError(f"Unknown objective {objective}")
s.minimize(objective)

print("Solving...")
# print("using objective", objective)
t0 = time.time()
res = s.check()
t1 = time.time()
print(f"Optimization took {t1-t0:.2f} seconds")

def get_float(expr):
    return float(expr.numerator_as_long())/float(expr.denominator_as_long())

if res == sat:
    print("Solution found")
    print()
    m = s.model()
    print(f"Producing {m.evaluate(goal_resource)} {goal_item} at quality {qualityName(goal_quality, padding=False)}")
    print(f"Objective ({org_objective}): {get_float(m.evaluate(objective)):.2f}")
    
    print()
    print("Resources:")
    for resource, quality_amounts in inputs.items():
        print(f"  {itemName(resource)}: ")
        for quality, amount in sorted(quality_amounts.items(), key=lambda x: x[0]):
            print(f"    {qualityName(quality)}: {get_float(m[amount]):.2f}")
    
    
    print()
    print("Machines:")
    for ri, recipe in enumerate(recipes):
        print(f"  {recipe.name} crafted in {recipe.machine.name}: ")
        for q in range(max_quality+1):
            amount = get_float(m[recipe_amounts[ri][q]])
            if amount > 0:
                print(f"    {qualityName(q)}: {amount:.2f}")
            
    print()
    print("Left over resources:")
    for resource, quality_amounts in resources.items():
        print(f"  {itemName(resource)}: ")
        for quality, amount in sorted(quality_amounts.items(), key=lambda x: x[0]):
            amount = get_float(m.evaluate(amount))
            if amount > 0:
                print(f"    {qualityName(quality)}: {amount:.2f}")
else:
    print("No solution found")
