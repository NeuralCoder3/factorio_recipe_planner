import time
from dataclasses import dataclass
from collections import defaultdict
import math

# mode = "z3"
# mode = "mip"
mode = "gurobi"

# objective = "overhead"
objective = "inputs"

# goal_item = "green_circuit"
# goal_quality = 2
# goal_item = "red_circuit"
# goal_quality = 2
# goal_item = "blue_circuit"
# goal_quality = 2

goal_item = "blue_circuit"
goal_quality = 2

rarities = ["normal", "uncommon", "rare", "epic", "legendary"]
max_quality = 2
# max_quality = len(rarities)-1
quality_module_percentage = 0.02 # 2% for quality level 2 module
productivity_module_percentage = 0.06 # 6% for productivity level 2 module

item_productivity = {
    # productivity research (e.g. steel)
}

# TODO: scaling of input priority => water 0
input_items = ["iron_ore_vein", "copper_ore_vein", "coal_vein", "petroleum_gas", "water", "calcite"]
recycle_percentage = 0.25
quality_module_name = "quality lv 2"
productivity_module_name = "productivity lv 2"

class Wrapper:
    def __init__(self, obj):
        self.obj = obj
        self.overwritten = {}
        # delayed to avoid infinite recursion in self.obj = obj
        self.__setattr__ = self.__setattr__2
        
    def __setattr__2(self, name, value):
        self.overwritten[name] = value
        
    # forward all non overwritten attributes to the object
    def __getattr__(self, name):
        if name in self.overwritten:
            return self.overwritten[name]
        return getattr(self.obj, name)

if mode == "mip":
    # compatibility layer for mip to z3
    from mip import *
    s = Model(sense=MINIMIZE, solver_name=CBC)
    
    def Real(name):
        return s.add_var(name=name, var_type=CONTINUOUS)
    
    def Int(name):
        return s.add_var(name=name, var_type=INTEGER)

    def add_constraint(expr):
        global s
        s += expr
        
    def minimize_objective(obj):
        global s
        s.objective = minimize(obj)

    s.add = add_constraint
    s.minimize = minimize_objective
    s.check = lambda: s.optimize()
    sat = OptimizationStatus.OPTIMAL
    
    class Model:
        def __init__(self, s):
            pass
        
        def evaluate(self, expr):
            if isinstance(expr, int):
                return expr
            value = expr.x
            return value
        
        # make subscripting work
        def __getitem__(self, key):
            return self.evaluate(key)
        
    s.model = lambda: Model(s)
        
elif mode == "z3":
    from z3 import *
    s = Optimize()
    
elif mode == "gurobi":
    
    from gurobipy import Model, GRB, quicksum, Var
    
    s = Model()
    s = Wrapper(s)
            
    
    def Real(name):
        return s.addVar(lb=0, name=name)
    
    def Int(name):
        return s.addVar(vtype=GRB.INTEGER, lb=0, name=name)
    
    def add_constraint(expr):
        global s
        s.addConstr(expr)
        
    def minimize_objective(obj):
        global s
        s.setObjective(obj, GRB.MINIMIZE)
        
    def check():
        global s
        s.optimize()
        print("Status:", s.status)
        return s.status

    s.add = add_constraint
    s.minimize = minimize_objective
    s.check = check
    sat = [2,9] # 2 = optimal, 9 = suboptimal
    
    class Model:
        def __init__(self, s):
            pass
        
        def access(self, e, f):
            if isinstance(e, int):
                return e
            value = f(e)
            return value
        
        
        def evaluate(self, expr):
            if isinstance(expr, Var):
                return self.__getitem__(expr)
            return self.access(expr, lambda x: x.getValue())
        
        # make subscripting work
        def __getitem__(self, key):
            return self.access(key, lambda x: x.X)
        
    s.model = lambda: Model(s)
    
    s.Params.TimeLimit = 10 # in seconds
    
else:
    raise ValueError(f"Unknown mode {mode}")


# map from resource -> quality -> amount
# per default, all resources are zero
# only for normal (quality=0) resources, we want the amount to be a Real
resources = defaultdict(lambda: defaultdict(lambda: 0))
inputs = defaultdict(lambda: defaultdict(lambda: 0))
for resource in input_items:
    v = Real(resource)
    resources[resource][0] = v
    inputs[resource][0] = v


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
    crafting_time : float = 1
    accepts_productivity : bool = True
    
def itemName(internal_name):
    # iron_ore => Iron Ore
    return " ".join([word.capitalize() for word in internal_name.split("_")])

def qualityName(quality, padding=True):
    max_len = max(len(r) for r in rarities)
    name = rarities[quality]
    if not padding:
        return name
    return " " * (max_len - len(name)) + name # + f" ({quality})"

fluids = set([
    "water", "crude_oil", "heavy_oil", "light_oil", "petroleum_gas", "sulfuric_acid", "lubricant",
    "steam", 
    "molten_iron", "molten_copper", 
])
unrecycleable = set(
    # fluids
    list(fluids)+[
        # ambiguous resources (already covered)
        # raw resources
        "iron_ore_vein", "copper_ore_vein", "coal_vein",
        "iron_ore", "copper_ore", "coal", "stone", "uranium_ore", "raw_fish", "wood", "calcite"
        # other processes
        "uranium_235", "uranium_238", 
        # smelting
        "iron_plate", "copper_plate", 
        # can things that produce more than 1 be recycled?
        # yes => copper cable works
    ]
)
    
miner = Machine(
    "Miner",
    module_slots=3,
    speed=0.5,
    productivity=0.3
)

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

chemical_plant = Machine(
    "Chemical Plant",
    module_slots=3,
    speed=1
)

recycler = Machine(
    "Recycler",
    module_slots=4,
    speed=0.5
)

foundry = Machine(
    "Foundry",
    module_slots=4,
    speed=4,
    productivity=0.5
)

exclude_machines = [
    # foundry
]
allow_recycling = recycler not in exclude_machines

recipes = [
    Recipe(
        name="Mine Copper",
        machine=miner,
        inputs={"copper_ore_vein": 1},
        outputs={"copper_ore": 1},
        crafting_time=1
    ),
    Recipe(
        name="Mine Iron",
        machine=miner,
        inputs={"iron_ore_vein": 1},
        outputs={"iron_ore": 1},
        crafting_time=1
    ),
    Recipe(
        name="Mine Coal",
        machine=miner,
        inputs={"coal_vein": 1},
        outputs={"coal": 1},
        crafting_time=1
    ),
    Recipe(
        name="Copper Smelting",
        machine=smelter,
        inputs={"copper_ore": 1},
        outputs={"copper_plate": 1},
        crafting_time=3.2
    ),
    Recipe(
        name="Iron Smelting",
        machine=smelter,
        inputs={"iron_ore": 1},
        outputs={"iron_plate": 1},
        crafting_time=3.2
    ),
    Recipe(
        name="Copper Wire",
        machine=assembler,
        inputs={"copper_plate": 1},
        outputs={"copper_wire": 2},
        crafting_time=0.5
    ),
    Recipe(
        name="Green Circuits",
        machine=assembler,
        inputs={"copper_wire": 3, "iron_plate": 1},
        outputs={"green_circuit": 1},
        crafting_time=0.5
    ),
    Recipe(
        name="Plastic",
        machine=chemical_plant,
        inputs={"coal": 1, "petroleum_gas": 20},
        outputs={"plastic": 2},
        crafting_time=1
    ),
    Recipe(
        name="Red Circuits",
        machine=assembler,
        inputs={"copper_wire": 4, "plastic": 2, "green_circuit": 2},
        outputs={"red_circuit": 1},
        crafting_time=6
    ),
    Recipe(
        name="Sulfur",
        machine=chemical_plant,
        inputs={"water": 30, "petroleum_gas": 30},
        outputs={"sulfur": 2},
        crafting_time=1
    ),
    Recipe(
        name="Sulfuric Acid",
        machine=chemical_plant,
        inputs={"iron_plate": 1, "sulfur": 5, "water": 100},
        outputs={"sulfuric_acid": 50},
        crafting_time=1
    ),
    Recipe(
        name="Blue Circuit",
        machine=assembler,
        inputs={"red_circuit": 2, "green_circuit": 20, "sulfuric_acid": 5},
        outputs={"blue_circuit": 1},
        crafting_time=10
    ),
    Recipe(
        name="Melt Iron",
        machine=foundry,
        inputs={"iron_ore": 50, "calcite": 1},
        outputs={"molten_iron": 500},
        crafting_time=32
    ),
    Recipe(
        name="Cast Iron",
        machine=foundry,
        inputs={"molten_iron": 20},
        outputs={"iron_plate": 2},
        crafting_time=3.2
    ),
    Recipe(
        name="Melt Copper",
        machine=foundry,
        inputs={"copper_ore": 50, "calcite": 1},
        outputs={"molten_copper": 500},
        crafting_time=32
    ),
    Recipe(
        name="Cast Copper",
        machine=foundry,
        inputs={"molten_copper": 20},
        outputs={"copper_plate": 2},
        crafting_time=3.2
    ),
    Recipe(
        name="Cast Copper Wire",
        machine=foundry,
        inputs={"molten_copper": 5},
        outputs={"copper_wire": 2},
        crafting_time=1
    ),
]

recipes = [r for r in recipes if r.machine not in exclude_machines]

recycle_times = {
    # https://wiki.factorio.com/Recycler
    # time (in s) per item
    "blue_circuit": 1/0.8,
    "red_circuit": 1/1.33,
    "low_density_structure": 1/0.5,
}

recycle_recipes = []
recycle_map = {}
recipe_count = len(recipes)
if allow_recycling:
    i = 0
    for ri, recipe in enumerate(recipes):
        if len(recipe.outputs) > 1:
            continue
        if any(out in unrecycleable for out in recipe.outputs):
            continue
        if all(inp in fluids for inp in recipe.inputs):
            continue
        recycle_outputs = {}
        for inp, amount in recipe.inputs.items():
            if inp in fluids:
                continue
            recycle_outputs[inp] = amount * recycle_percentage
        output_item = list(recipe.outputs.keys())[0]
        recycle_recipes.append(
            Recipe(
                name=f"Recycle {recipe.name}",
                machine=recycler,
                inputs=recipe.outputs,
                outputs=recycle_outputs,
                crafting_time=recycle_times.get(output_item, 1),
                accepts_productivity=False,
            )
        )
        recycle_map[ri] = i+recipe_count
        i+=1

# recipe -> quality -> amount
recipe_amounts = defaultdict(lambda: {})
# recipe -> quality -> module -> amount
modules_amounts = \
    defaultdict(lambda: # recipe
        defaultdict(lambda: # quality
            {}
        )
    )
    
all_recipes = recipes + recycle_recipes
    
for ri, recipe in enumerate(all_recipes):
    machine = recipe.machine
    accepts_quality = not(all(out in fluids for out in recipe.outputs)) and not(all(inp in fluids for inp in recipe.inputs))
    # if output can not have quality => skip all stages
    quality_range = range(max_quality+1) if accepts_quality else [0]
    # here if recipe would not accept quality modules (can not happen except for testing)
    machine_productivity = machine.productivity
    for q in quality_range:
        recipe_amounts[ri][q] = Real(f"recipe_{ri}_q{q}")
        s.add(recipe_amounts[ri][q] >= 0)
        
        prod_amount = Int(f"prod_{ri}_q{q}") if recipe.accepts_productivity else 0
        quality_amount = Int(f"quality_{ri}_q{q}") if accepts_quality else 0
        s.add(quality_amount >= 0)
        s.add(prod_amount >= 0)
        s.add(quality_amount+prod_amount <= machine.module_slots)
        
        modules_amounts[ri][q][quality_module_name] = quality_amount
        modules_amounts[ri][q][productivity_module_name] = prod_amount
        
        for resource, amount in recipe.inputs.items():
            if resource in fluids:
                # fluids are always quality 0 => only use at quality 0
                # they do not contribute to quality considerations
                resources[resource][0] -= recipe_amounts[ri][q] * amount
                # fluids are not recycled
            else:
                resources[resource][q] -= recipe_amounts[ri][q] * amount
            
        for resource, amount in recipe.outputs.items():
            base_amount = recipe_amounts[ri][q] * amount
            # * prod
            # split with quality
            
            # TODO: force fluid quality
            
            # encode cubic constraint via bilinear method => double quadratic constraints
            base_amount_prod = Real(f"prod_amount_{ri}_q{q}_{resource}")
            item_prod = item_productivity.get(resource, 0)
            s.add(base_amount_prod == base_amount * (1 + productivity_module_percentage * prod_amount + item_prod + machine_productivity))
            
            percent_sum = 0
            if accepts_quality:
                # TODO: better sum directly instead of iterative
                percentage = quality_amount * quality_module_percentage
                for q2 in range(q+1,max_quality+1):
                    percent_sum += percentage
                    resources[resource][q2] += base_amount_prod * percentage
                    percentage /= 10
            resources[resource][q] += base_amount_prod * (1-percent_sum)

# no resource can be negative
for resource, quality_amounts in resources.items():
    for quality, amount in quality_amounts.items():
        s.add(amount >= 0)
        
goal_resource = resources[goal_item][goal_quality]
# for gurobi to print the resulting formula
# s.update()
# print(goal_resource)
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
t0 = time.time()
res = s.check()
t1 = time.time()
print(f"Optimization took {t1-t0:.2f} seconds")


def get_float(expr):
    if isinstance(expr, int):
        return expr
    if isinstance(expr, float):
        return expr
    return float(expr.numerator_as_long())/float(expr.denominator_as_long())

satisfied = False
if isinstance(sat, list):
    satisfied = res in sat
else:
    satisfied = res == sat

if satisfied:
    print("Solution found")
    print()
    m = s.model()
    print(f"Producing {get_float(m.evaluate(goal_resource)):.2f} {goal_item} at quality {qualityName(goal_quality, padding=False)}")
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
        machine_str = []
        for q in range(max_quality+1):
            if q not in recipe_amounts[ri]:
                continue
            amount = get_float(m[recipe_amounts[ri][q]])
            if ri in recycle_map and q in recipe_amounts[recycle_map[ri]]:
                rmi = recycle_map[ri]
                recycle_amount = get_float(m[recipe_amounts[rmi][q]])
                recycle_quality = abs(get_float(m[modules_amounts[rmi][q][quality_module_name]]))
                recycle_recipe = all_recipes[rmi]
                assert recycle_recipe.machine == recycler
                # TODO: use modules for time reduction
                recycler_count = recycle_amount * recycle_recipe.crafting_time / recycle_recipe.machine.speed
            else:
                recycle_amount = 0
            if amount > 0.01:
                machine_count = amount * recipe.crafting_time / recipe.machine.speed
                prod_amount = m[modules_amounts[ri][q][productivity_module_name]]
                quality_amount = m[modules_amounts[ri][q][quality_module_name]]
                prod_amount = abs(get_float(prod_amount))
                quality_amount = abs(get_float(quality_amount))
                s = ""
                s+=("    ")
                s+=(f"{qualityName(q)}: {amount:6.2f}")
                s+=(f" ({itemName(productivity_module_name)}: {prod_amount}, {itemName(quality_module_name)}: {quality_amount})")
                if recycle_amount > 0.01:
                    # TODO: use modules for time reduction
                    s+=(f" (Recycle: {recycle_amount:6.2f}, {itemName(quality_module_name)}: {recycle_quality})")
                # s+=("\n")
                # s+=("    ")
                # s+=(" "*len(qualityName(q)))
                # s+=("  ")
                # s+=(f"{math.ceil(machine_count):3} {recipe.machine.name}")
                # if recycle_amount > 0.01:
                #     s+=(", ")
                #     s+=(f"{math.ceil(recycler_count):3} Recycler")
                s+=("  => ")
                s+=(f"{math.ceil(machine_count)} {recipe.machine.name}")
                if recycle_amount > 0.01:
                    s+=(", ")
                    s+=(f"{math.ceil(recycler_count)} Recycler")
                machine_str.append(s)
        if machine_str:
            print(f"  {recipe.name} in {recipe.machine.name}: ")
            print("\n".join(machine_str))
            
    print()
    print("Leftover resources:")
    for resource, quality_amounts in resources.items():
        resource_str = []
        for quality, amount in sorted(quality_amounts.items(), key=lambda x: x[0]):
            amount = get_float(m.evaluate(amount))
            if amount > 0.01:
                resource_str.append(f"    {qualityName(quality)}: {amount:.2f}")
        if resource_str:
            print(f"  {itemName(resource)}: ")
            print("\n".join(resource_str))
else:
    print("No solution found")
