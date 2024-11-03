from common import *
from solver import *

# map from resource -> quality -> amount
# per default, all resources are zero
# only for normal (quality=0) resources, we want the amount to be a Real
resources = defaultdict(lambda: defaultdict(lambda: 0))
inputs = defaultdict(lambda: defaultdict(lambda: 0))
for resource in input_items:
    v = Real(resource)
    resources[resource][0] = v
    inputs[resource][0] = v

# recipe -> quality -> amount
recipe_amounts = defaultdict(lambda: {})
# recipe -> quality -> module -> amount
modules_amounts = \
    defaultdict(lambda: # recipe
        defaultdict(lambda: # quality
            {}
        )
    )

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
                    actual_percentage = percentage * (0.9 if q2 != max_quality else 1)
                    percent_sum += actual_percentage
                    resources[resource][q2] += base_amount_prod * actual_percentage
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
