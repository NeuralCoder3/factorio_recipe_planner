from common import *
from solver import *
import time

def deepsum(d):
    if isinstance(d, dict):
        return sum(deepsum(v) for v in d.values())
    return d

# map from planet -> resource -> quality -> amount
# per default, all resources are zero
# only for normal (quality=0) resources, we want the amount to be a Real
resources = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: 0)))
scaled_inputs = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: 0)))
inputs = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: 0)))
for planet, planet_resources in inputs_per_planet.items():
    for resource, scaling in planet_resources.items():
        v = Real(f"resource_{resource}_{planet}_q0")
        inputs[planet][resource][0] = v
        scaled_inputs[planet][resource][0] = v * scaling
        resources[planet][resource][0] = v

# map from machine -> quality -> amount
machines = defaultdict(lambda: defaultdict(lambda: 0))

# planet -> recipe -> recipe quality -> machine quality -> #quality_modules -> #prod_modules -> #speed_modules -> #speed_beacons -> amount
recipe_amounts = \
    defaultdict(lambda: # planet
        defaultdict(lambda: # recipe
            defaultdict(lambda: # recipe quality
                defaultdict(lambda: # machine quality
                    defaultdict(lambda: # #quality_modules
                        defaultdict(lambda: # #prod_modules
                            defaultdict(lambda: # #speed_modules
                                {} #speed_beacons -> amount
                            )
                        )
                    )
                )
            )
        )
    )

speed_modules_used = Real("speed_modules_used")
quality_modules_used = Real("quality_modules_used")
prod_modules_used = Real("prod_modules_used")
beacons_used = Real("beacons_used")


tstart = time.time()
for ri, recipe in enumerate(all_recipes):
    accepts_quality = not(all(out in fluids for out in recipe.outputs)) and not(all(inp in fluids for inp in recipe.inputs)) and recipe.accepts_quality
    # if output can not have quality => skip all stages
    quality_range = range(max_quality+1) if accepts_quality else [0]
    if recipe.forced_quality is not None:
        quality_range = [recipe.forced_quality]

    for planet in recipe.allowed_planets:
        if planet not in recipe.machine.allowed_planets:
            continue 
        if planet in exclude_planets:
            continue

        #print(f"Processing recipe {recipe.name} on planet {planet}. Machine allowed on {recipe.machine.allowed_planets}")

        for q in quality_range:
            max_machine_quality = max_quality if objective == "constrained" else 0
            for machine_q in range(max_machine_quality+1):
                max_quality_modules = recipe.machine.module_slots if accepts_quality and recipe.accepts_quality_module else 0
                for num_quality_modules in range(max_quality_modules+1):
                    max_prod_modules = recipe.machine.module_slots - num_quality_modules if recipe.accepts_productivity else 0
                    for num_productivity_modules in range(max_prod_modules+1):
                        max_speed_modules = recipe.machine.module_slots - num_quality_modules - num_productivity_modules #if objective == "constrained" else 0
                        for num_speed_modules in range(max_speed_modules+1):
                            max_beacons = max_beacons_per_machine #if objective == "constrained" else 0
                            for num_beacons in range(max_beacons+1):
                                recipe_amount = Real(f"recipe_{ri}_{recipe.name.replace(' ', '-')}_{planet}_qr{q}_qm{machine_q}_nq{num_quality_modules}_np{num_productivity_modules}_ns{num_speed_modules}_nb{num_beacons}")
                                recipe_amounts[planet][ri][q][machine_q][num_quality_modules][num_productivity_modules][num_speed_modules][num_beacons] = recipe_amount
                                s.add(recipe_amount >= 0)

                                speed_bonus = 1
                                speed_bonus += speed_module.speed_bonus * (num_speed_modules + math.sqrt(num_beacons) * beacon.distribution_efficiency * 2)
                                speed_bonus += quality_module.speed_bonus * num_quality_modules
                                speed_bonus += productivity_module.speed_bonus * num_productivity_modules
                                speed_bonus = max(0.2, speed_bonus)

                                productivity_bonus = 1
                                productivity_bonus += recipe.productivity
                                productivity_bonus += recipe.machine.productivity
                                productivity_bonus += productivity_module.productivity_bonus * num_productivity_modules
                                productivity_bonus += quality_module.productivity_bonus * num_quality_modules
                                productivity_bonus += speed_module.productivity_bonus * num_speed_modules
                                productivity_bonus = max(1.0, productivity_bonus)

                                quality_bonus = 0
                                quality_bonus += quality_module.quality_bonus * num_quality_modules
                                quality_bonus += productivity_module.quality_bonus * num_productivity_modules
                                quality_bonus += speed_module.quality_bonus * (num_speed_modules + math.sqrt(num_beacons) * beacon.distribution_efficiency * 2)
                                quality_bonus = max(0, quality_bonus)

                                machine_count = recipe_amount * recipe.crafting_time / recipe.machine.qspeed[machine_q] / speed_bonus
                                machines[recipe.machine.name][machine_q] += machine_count

                                speed_modules_used += machine_count * (num_speed_modules + num_beacons * beacon_sharedness * 2)
                                quality_modules_used += machine_count * num_quality_modules
                                prod_modules_used += machine_count * num_productivity_modules
                                beacons_used += machine_count * num_beacons * beacon_sharedness
                                
                                input_planet = recipe.forced_input_planet if recipe.forced_input_planet is not None else planet
                                output_planet = recipe.forced_output_planet if recipe.forced_output_planet is not None else planet

                                for resource, resource_amount in recipe.inputs.items():
                                    input_quality = recipe.forced_input_quality.get(resource, q) if resource not in fluids else 0
                                    resources[input_planet][resource][input_quality] -= recipe_amount * resource_amount
                                    
                                for resource, resource_amount in recipe.outputs.items():
                                    base_amount = resource_amount * productivity_bonus
                                    
                                    percent_sum = 0
                                    output_quality = recipe.forced_output_quality.get(resource, q) if resource not in fluids else 0
                                    is_forced_quality = resource in recipe.forced_output_quality or resource in fluids
                                    if accepts_quality and not is_forced_quality:
                                        # TODO: better sum directly instead of iterative
                                        percentage = quality_bonus
                                        for q2 in range(q+1,max_quality+1):
                                            actual_percentage = percentage * (0.9 if q2 != max_quality else 1)
                                            percent_sum += actual_percentage
                                            resources[output_planet][resource][q2] += recipe_amount * (base_amount * actual_percentage)
                                            percentage /= 10
                                    resources[output_planet][resource][output_quality] += recipe_amount * (base_amount * (1-percent_sum))

# no resource can be negative
for planet in all_planets + ["space"]:
    for resource, quality_amounts in resources[planet].items():
        for quality, amount in quality_amounts.items():
            s.add(amount >= 0)

if goal_planet is not None:
    goal_resource = resources[goal_planet][goal_item][goal_quality]
else:
    goal_resource = sum(resources[planet][goal_item][goal_quality] for planet in all_planets + ["space"])

input_cost = deepsum(scaled_inputs)
overhead_cost = deepsum(resources)
machine_cost = deepsum(machines) + beacons_used + speed_modules_used + quality_modules_used + prod_modules_used
space_travel_cost = machines["Rocket"][0]

org_objective =  objective
if objective == "inputs":
    objective = input_cost + machine_cost * 10 + (space_travel_cost * 100000 if reduce_space_travel else 0)
    s.add(goal_resource >= goal_amount)
elif objective == "overhead":
    objective = overhead_cost + machine_cost * 10
    s.add(overhead_cost >= goal_amount)
elif objective == "constrained":
    objective = -goal_resource + machine_cost / 1e6
    s.add(speed_modules_used <= available_speed_modules)
    s.add(quality_modules_used <= available_quality_modules)
    s.add(prod_modules_used <= available_prod_modules)
    s.add(beacons_used <= available_beacons)
    for machine, quality_amounts in machines.items():
        for quality, amount in quality_amounts.items():
            s.add(amount <= available_machines[machine][quality])
else:
    raise ValueError(f"Unknown objective {objective}")
s.minimize(objective)
# for gurobi to print the resulting formula
# s.update()
#print(s.display())
# s.write('tmp.lp')

t0 = time.time()
print(f"Building solver problem took {t0-tstart:.2f} seconds")
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
    print(f"Resources ({get_float(m.evaluate(deepsum(inputs))):0.2f}):")
    for planet in all_planets + ["space"]:
        if abs(m.evaluate(deepsum(inputs[planet]))) < eps:
            continue
        print(f"  {planetName(planet)}: ")
        for resource, quality_amounts in inputs[planet].items():
            if abs(m.evaluate(sum(quality_amounts.values()))) < eps:
                continue
            print(f"    {itemName(resource)}: ")
            for quality, amount in sorted(quality_amounts.items(), key=lambda x: x[0]):
                if abs(get_float(m[amount])) < eps:
                    continue
                print(f"      {qualityName(quality)}: {get_float(m[amount]):.2f}")
    
    
    print()
    print("Machines:")
    for planet in all_planets + ["space"]:
        if planet not in recipe_amounts:
            continue
        if abs(m.evaluate(deepsum(recipe_amounts[planet]))) < eps:
            continue

        print(f"  {planetName(planet)}: ")
        for ri, recipe in enumerate(all_recipes):
            for machine_q in range(max_quality+1):
                machine_str = []
                for q in range(max_quality+1):
                    if q not in recipe_amounts[planet][ri]:
                        continue
                    if machine_q not in recipe_amounts[planet][ri][q]:
                        continue
                    for num_quality_modules in range(recipe.machine.module_slots+1):
                        if num_quality_modules not in recipe_amounts[planet][ri][q][machine_q]:
                            continue
                        for num_productivity_modules in range(recipe.machine.module_slots - num_quality_modules + 1):
                            if num_productivity_modules not in recipe_amounts[planet][ri][q][machine_q][num_quality_modules]:
                                continue
                            for num_speed_modules in range(recipe.machine.module_slots - num_quality_modules - num_productivity_modules + 1):
                                if num_speed_modules not in recipe_amounts[planet][ri][q][machine_q][num_quality_modules][num_productivity_modules]:
                                    continue
                                for num_beacons in range(max_beacons_per_machine+1):
                                    if num_beacons not in recipe_amounts[planet][ri][q][machine_q][num_quality_modules][num_productivity_modules][num_speed_modules]:
                                        continue

                                    recipe_amount = get_float(m[recipe_amounts[planet][ri][q][machine_q][num_quality_modules][num_productivity_modules][num_speed_modules][num_beacons]])
                                    if abs(recipe_amount) > eps:
                                        speed_bonus = 1
                                        speed_bonus += speed_module.speed_bonus * (num_speed_modules + math.sqrt(num_beacons) * beacon.distribution_efficiency * 2)
                                        speed_bonus += quality_module.speed_bonus * num_quality_modules
                                        speed_bonus += productivity_module.speed_bonus * num_productivity_modules
                                        speed_bonus = max(0.2, speed_bonus)

                                        productivity_bonus = 1
                                        productivity_bonus += recipe.productivity
                                        productivity_bonus += recipe.machine.productivity
                                        productivity_bonus += productivity_module.productivity_bonus * num_productivity_modules
                                        productivity_bonus += quality_module.productivity_bonus * num_quality_modules
                                        productivity_bonus += speed_module.productivity_bonus * num_speed_modules
                                        productivity_bonus = max(1.0, productivity_bonus)

                                        machine_count = recipe_amount * recipe.crafting_time / recipe.machine.speed / speed_bonus
                                        s = ""
                                        s+=("      ")
                                        s+=(f"{qualityName(q)}: {recipe_amount:6.2f}")
                                        s+=(f" ({itemName(productivity_module.name)}: {num_productivity_modules}, {itemName(quality_module.name)}: {num_quality_modules}, {itemName(speed_module.name)}: {num_speed_modules}, {itemName(beacon.name)}: {num_beacons})")
                                        s+=("  => ")
                                        s+=(f"{math.ceil(machine_count):>4} {recipe.machine.name:}: ")
                                        s+=" + ".join( [f"{recipe_amount*resource_amount*speed_bonus:.2f}/s {itemName(resource)}" for resource, resource_amount in recipe.inputs.items()])
                                        s+=" -> "
                                        s+=" + ".join( [f"{recipe_amount*resource_amount*speed_bonus*productivity_bonus:.2f}/s {itemName(resource)}" for resource, resource_amount in recipe.outputs.items()])
                                        
                                        machine_str.append(s)
                if machine_str:
                    print(f"    {recipe.name} in {recipe.machine.name} ({qualityName(machine_q, padding=False)}): ")
                    print("\n".join(machine_str))
            
    print()
    print(f"Total machines used ({get_float(m.evaluate(deepsum(machines))):.2f}):")
    for machine, quality_amounts in machines.items():
        machine_str = []
        for quality, amount in sorted(quality_amounts.items(), key=lambda x: x[0]):
            amount = get_float(m.evaluate(amount))
            if amount > eps:
                machine_str.append(f"    {qualityName(quality)}: {amount:.2f}")
        if machine_str:
            print(f"  {machine}: ")
            print("\n".join(machine_str))

    print()
    print(f"Total modules used ({get_float(m.evaluate(deepsum(speed_modules_used+quality_modules_used+prod_modules_used))):0.2f}):")
    print(f"  {itemName(speed_module.name)}: {get_float(m.evaluate(speed_modules_used)):.2f}")
    print(f"  {itemName(quality_module.name)}: {get_float(m.evaluate(quality_modules_used)):.2f}")
    print(f"  {itemName(productivity_module.name)}: {get_float(m.evaluate(prod_modules_used)):.2f}")
    print(f"  {beacon.name}: {get_float(m.evaluate(beacons_used)):.2f}")

    print()
    print(f"Leftover resources ({get_float(m.evaluate(deepsum(resources))):0.2f}):")
    for planet in all_planets + ["space"]:
        if abs(m.evaluate(deepsum(resources[planet]))) < eps:
            continue
        print(f"  {planetName(planet)}: ")
        for resource, quality_amounts in resources[planet].items():
            resource_str = []
            for quality, amount in sorted(quality_amounts.items(), key=lambda x: x[0]):
                amount = get_float(m.evaluate(amount))
                if abs(amount) > eps:
                    resource_str.append(f"      {qualityName(quality)}: {amount:.2f}")
            if resource_str:
                print(f"    {itemName(resource)}: ")
                print("\n".join(resource_str))
else:
    print("No solution found")
