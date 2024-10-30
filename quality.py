import time
from dataclasses import dataclass
from collections import defaultdict

# mode = "z3"
# mode = "mip"
mode = "gurobi"

# objective = "overhead"
objective = "inputs"

# goal_item = "green_circuit"
# goal_quality = 2
goal_item = "red_circuit"
goal_quality = 2

input_items = ["iron_ore", "copper_ore", "coal", "petroleum_gas"]
rarities = ["normal", "uncommon", "rare", "epic", "legendary"]
max_quality = 2
quality_module_percentage = 0.02 # 2% for quality level 2 module
productivity_module_percentage = 0.06 # 6% for productivity level 2 module
quality_module_name = "quality"
productivity_module_name = "productivity"


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

# for multiple non-z3 solvers that directly return a float
class FloatWrapper(Wrapper):
    def __init__(self, obj):
        obj = abs(obj)
        super().__init__(obj)
        self.numerator_as_long = lambda : self.obj
        self.denominator_as_long = lambda : 1
        
    def __str__(self):
        # format overloading is difficult => do it manual for now
        return f"{self.obj:.2f}"
        
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
            if isinstance(value, float):
                return FloatWrapper(value)
            return value
        
        # make subscripting work
        def __getitem__(self, key):
            return self.evaluate(key)
        
    s.model = lambda: Model(s)
        
elif mode == "z3":
    from z3 import *
    s = Optimize()
    
elif mode == "gurobi":
    
    from gurobipy import Model, GRB, quicksum
    
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
    sat = 2
    
    class Model:
        def __init__(self, s):
            pass
        
        def access(self, e, f):
            if isinstance(e, int):
                return e
            value = f(e)
            if isinstance(value, float):
                return FloatWrapper(value)
            return value
        
        
        def evaluate(self, expr):
            return self.access(expr, lambda x: x.getValue())
        
        # make subscripting work
        def __getitem__(self, key):
            return self.access(key, lambda x: x.X)
        
    s.model = lambda: Model(s)
    
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

fluids = set(["water", "crude_oil", "heavy_oil", "light_oil", "petroleum_gas", "sulfuric_acid", "lubricant"])
    
miner = Machine(
    "Miner",
    module_slots=3,
    speed=0.5
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
    ),
    Recipe(
        name="Plastic",
        machine=chemical_plant,
        inputs={"coal": 1, "petroleum_gas": 20},
        outputs={"plastic": 2},
    ),
    Recipe(
        name="Red Circuits",
        machine=assembler,
        inputs={"copper_wire": 4, "plastic": 2, "green_circuit": 2},
        outputs={"red_circuit": 1}
    )
]

# recipe -> quality -> amount
recipe_amounts = defaultdict(lambda: {})
recycle_amounts = defaultdict(lambda: {})
# recipe -> quality -> module -> amount
modules_amounts = \
    defaultdict(lambda: # recipe
        defaultdict(lambda: # quality
            {}
        )
    )

for ri, recipe in enumerate(recipes):
    machine = recipe.machine
    accepts_quality = not(all(out in fluids for out in recipe.outputs))
    quality_range = range(max_quality+1) if accepts_quality else [0]
    for q in quality_range:
        recipe_amounts[ri][q] = Real(f"recipe_{ri}_q{q}")
        s.add(recipe_amounts[ri][q] >= 0)
        for resource, amount in recipe.inputs.items():
            if resource in fluids:
                # fluids are always quality 0 => only use at quality 0
                # they do not contribute to quality considerations
                resources[resource][0] -= recipe_amounts[ri][q] * amount
            else:
                resources[resource][q] -= recipe_amounts[ri][q] * amount
            
        for resource, amount in recipe.outputs.items():
            base_amount = recipe_amounts[ri][q] * amount
            # * prod
            # split with quality
            
            prod_amount = Int(f"prod_{ri}_q{q}") if recipe.accepts_productivity else 0
            quality_amount = Int(f"quality_{ri}_q{q}") if accepts_quality else 0
            s.add(quality_amount >= 0)
            s.add(prod_amount >= 0)
            s.add(quality_amount+prod_amount <= machine.module_slots)
            
            modules_amounts[ri][q][quality_module_percentage] = quality_amount
            modules_amounts[ri][q][productivity_module_name] = prod_amount
            
            # encode cubic constraint via bilinear method => double quadratic constraints
            base_amount_prod = Real(f"prod_amount_{ri}_q{q}")
            s.add(base_amount_prod == base_amount * (1 + productivity_module_percentage * prod_amount))
            
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
            if q not in recipe_amounts[ri]:
                continue
            amount = get_float(m[recipe_amounts[ri][q]])
            if amount > 0:
                prod_amount = m[modules_amounts[ri][q][productivity_module_name]]
                quality_amount = m[modules_amounts[ri][q][quality_module_percentage]]
                print(f"    {qualityName(q)}: {amount:6.2f} ({itemName(productivity_module_name)}: {prod_amount}, {itemName(quality_module_name)}: {quality_amount})")
            
    print()
    print("Left over resources:")
    for resource, quality_amounts in resources.items():
        print(f"  {itemName(resource)}: ")
        for quality, amount in sorted(quality_amounts.items(), key=lambda x: x[0]):
            amount = get_float(m.evaluate(amount))
            if amount > 0.001:
                print(f"    {qualityName(quality)}: {amount:.2f}")
else:
    print("No solution found")
