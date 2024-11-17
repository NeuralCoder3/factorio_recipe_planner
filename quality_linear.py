import json
from common import *
from solver import *
import time
from typing import Any

def deepsum(d):
    if isinstance(d, dict):
        return sum(deepsum(v) for v in d.values())
    if isinstance(d, list):
        return sum(deepsum(v) for v in d)
    return d

# map from planet -> resource -> quality -> amount
# per default, all resources are zero
# only for normal (quality=0) resources, we want the amount to be a Real
resources: defaultdict[str, defaultdict[str, defaultdict[int, Any]]] = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: 0)))
scaled_inputs: defaultdict[str, defaultdict[str, defaultdict[int, Any]]] = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: 0)))
inputs: defaultdict[str, defaultdict[str, defaultdict[int, Any]]] = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: 0)))
for planet, planet_resources in inputs_per_planet.items():
    for resource, scaling in planet_resources.items():
        v = Real(f"resource_{resource}_{planet}_q0")
        inputs[planet][resource][0] = v
        scaled_inputs[planet][resource][0] = v * scaling
        resources[planet][resource][0] = v

# map from planet -> machine -> quality -> amount
machines: defaultdict[str, defaultdict[Machine, defaultdict[int, Any]]] = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: 0)))

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
true_machines_per_recipe = \
    defaultdict(lambda: # planet
        defaultdict(lambda: # recipe
            defaultdict(lambda: # recipe quality
                defaultdict(lambda: # machine quality
                    defaultdict(lambda: # #quality_modules
                        defaultdict(lambda: # #prod_modules
                            defaultdict(lambda: # #speed_modules
                                defaultdict(lambda: #speed_beacons
                                    0 # amount
                                )
                            )
                        )
                    )
                )
            )
        )
    )

# each is planet -> count
speed_modules_used = defaultdict(lambda: 0)
quality_modules_used = defaultdict(lambda: 0)
prod_modules_used = defaultdict(lambda: 0)
beacons_used = defaultdict(lambda: 0)


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
            max_machine_quality = min(max_quality, recipe.machine.max_quality) # if objective == "constrained" else 0
            for machine_q in range(max_machine_quality+1):
                max_quality_modules = recipe.machine.module_slots if not(all(out in fluids for out in recipe.outputs)) and recipe.accepts_quality_module else 0
                for num_quality_modules in range(max_quality_modules+1):
                    max_prod_modules = recipe.machine.module_slots - num_quality_modules if recipe.accepts_productivity else 0
                    for num_productivity_modules in range(max_prod_modules+1):
                        max_speed_modules = recipe.machine.module_slots - num_quality_modules - num_productivity_modules if recipe.accepts_speed else 0
                        for num_speed_modules in range(max_speed_modules+1):
                            max_beacons = max_beacons_per_machine if recipe.accepts_speed else 0
                            for num_beacons in range(max_beacons+1):
                                recipe_amount = Real(f"recipe_{ri}_{recipe.name.replace(' ', '-')}_{planet}_qr{q}_qm{machine_q}_nq{num_quality_modules}_np{num_productivity_modules}_ns{num_speed_modules}_nb{num_beacons}")
                                recipe_amounts[planet][ri][q][machine_q][num_quality_modules][num_productivity_modules][num_speed_modules][num_beacons] = recipe_amount
                                s.add(recipe_amount >= 0)

                                effective_num_speed_modules = num_speed_modules + num_beacons * beacon.distribution_efficiency * 2

                                speed_bonus = 1
                                speed_bonus += speed_module.speed_bonus * effective_num_speed_modules
                                speed_bonus += quality_module.speed_bonus * num_quality_modules
                                speed_bonus += productivity_module.speed_bonus * num_productivity_modules
                                speed_bonus = max(0.2, speed_bonus)

                                productivity_bonus = 1
                                productivity_bonus += recipe.productivity
                                productivity_bonus += recipe.machine.productivity
                                productivity_bonus += productivity_module.productivity_bonus * num_productivity_modules
                                productivity_bonus += quality_module.productivity_bonus * num_quality_modules
                                productivity_bonus += speed_module.productivity_bonus * effective_num_speed_modules
                                productivity_bonus = max(1.0, productivity_bonus)

                                quality_bonus = 0
                                quality_bonus += quality_module.quality_bonus * num_quality_modules
                                quality_bonus += productivity_module.quality_bonus * num_productivity_modules
                                quality_bonus += speed_module.quality_bonus * effective_num_speed_modules
                                quality_bonus = max(0, quality_bonus)

                                machine_count = recipe_amount * recipe.crafting_time / recipe.machine.qspeed[machine_q] / speed_bonus

                                if objective == "inputs_cost_matrix" and recipe.machine.underlying_item is not None:
                                    # initially not an integer, will be made one in a later step
                                    integer_machine_count = Real(f"machine_count_{ri}_{recipe.machine.name.replace(' ', '-')}_{planet}_qr{q}_qm{machine_q}_nq{num_quality_modules}_np{num_productivity_modules}_ns{num_speed_modules}_nb{num_beacons}")
                                    s.add(integer_machine_count >= machine_count)
                                    # s.add(integer_machine_count <= machine_count + 1 + 1e-6)
                                    machine_count = integer_machine_count
                                    true_machines_per_recipe[planet][ri][q][machine_q][num_quality_modules][num_productivity_modules][num_speed_modules][num_beacons] = integer_machine_count

                                machines[planet][recipe.machine][machine_q] += machine_count

                                speed_modules_used[planet] += machine_count * (num_speed_modules + num_beacons * beacon_sharedness * 2)
                                quality_modules_used[planet] += machine_count * num_quality_modules
                                prod_modules_used[planet] += machine_count * num_productivity_modules
                                beacons_used[planet] += machine_count * num_beacons * beacon_sharedness
                                
                                input_planet = recipe.forced_input_planet if recipe.forced_input_planet is not None else planet
                                output_planet = recipe.forced_output_planet if recipe.forced_output_planet is not None else planet

                                for resource, resource_amount in recipe.inputs.items():
                                    input_quality = recipe.forced_input_quality.get(resource, q) if resource not in fluids else 0
                                    resources[input_planet][resource][input_quality] -= recipe_amount * resource_amount
                                    
                                for resource, resource_amount in recipe.outputs.items():
                                    in_amount = recipe.inputs.get(resource, 0)
                                    base_amount = max(resource_amount, in_amount + (resource_amount - in_amount) * productivity_bonus)
                                    base_amount *= recipe_amount

                                    
                                    percent_sum = 0
                                    output_quality = recipe.forced_output_quality.get(resource, q) if resource not in fluids else 0
                                    is_forced_quality = resource in recipe.forced_output_quality or resource in fluids
                                    if accepts_quality and not is_forced_quality:
                                        # TODO: better sum directly instead of iterative
                                        percentage = quality_bonus
                                        for q2 in range(q+1,max_quality+1):
                                            actual_percentage = percentage * (0.9 if q2 != max_quality else 1)
                                            percent_sum += actual_percentage
                                            resources[output_planet][resource][q2] += base_amount * actual_percentage
                                            percentage /= 10
                                    resources[output_planet][resource][output_quality] += base_amount * (1-percent_sum)

# no resource can be negative
for planet in all_planets + ["space"]:
    for resource, quality_amounts in resources[planet].items():
        for quality, amount in quality_amounts.items():
            s.add(amount >= 0)
            
goal_resources = []
for g in goal:
    if g["planet"] is not None:
        goal_resources.append(resources[g["planet"]][g["item"]][g["quality"]])
    else:
        goal_resources.append(
            sum(resources[planet][g["item"]][g["quality"]] for planet in all_planets + ["space"])
        )

input_cost = deepsum(scaled_inputs)
overhead_cost = deepsum(resources)
machine_cost = deepsum(machines) + deepsum(beacons_used) + deepsum(speed_modules_used) + deepsum(quality_modules_used) + deepsum(prod_modules_used)
space_travel_cost = sum(machines[planet][rocket][0] for planet in all_planets)

org_objective =  objective
if objective == "inputs":
    objective = input_cost # + machine_cost * 10 + (space_travel_cost * 100000 if reduce_space_travel else 0)
    for gr,g in zip(goal_resources, goal):
        s.add(gr >= g["amount"])
elif objective == "inputs_cost_matrix":
    objective = input_cost
    hours_of_amortization = 1
    for planet, planet_machines in machines.items():
        for machine, quality_amounts in planet_machines.items():
            for quality, amount in quality_amounts.items():
                if machine.underlying_item is not None:
                    objective += amount * cost_matrix[planet][machine.underlying_item][quality] / (3600 * hours_of_amortization)

    for planet, num_beacons in beacons_used.items():
        objective += num_beacons * cost_matrix[planet][beacon.underlying_item][beacon.underlying_quality] / (3600 * hours_of_amortization)
    for planet, num_speed_modules in speed_modules_used.items():
        objective += num_speed_modules * cost_matrix[planet][speed_module.underlying_item][speed_module.underlying_quality] / (3600 * hours_of_amortization)
    for planet, num_quality_modules in quality_modules_used.items():
        objective += num_quality_modules * cost_matrix[planet][quality_module.underlying_item][quality_module.underlying_quality] / (3600 * hours_of_amortization)
    for planet, num_prod_modules in prod_modules_used.items():
        objective += num_prod_modules * cost_matrix[planet][productivity_module.underlying_item][productivity_module.underlying_quality] / (3600 * hours_of_amortization)
        
    if reduce_space_travel:
        objective += space_travel_cost * 100000

    for gr,g in zip(goal_resources, goal):
        s.add(gr >= g["amount"])
    s.minimize(objective)

    # preoptimize the actual recipes used
    print("Preoptimize recipe counts...")
    t0 = time.time()
    res = s.check()
    t1 = time.time()
    print(f"Preoptimization took {t1-t0:.2f} seconds")
    if not is_satisfied(res):
        print("No solution found")
        exit(0)

    m = s.model()

    # make machine counts integers and fix recipe counts
    
    for per_planet in recipe_amounts.values():
        for per_recipe in per_planet.values():
            for per_quality in per_recipe.values():
                current_usage = get_float(m.evaluate(deepsum(per_quality)))
                if current_usage < 1e-6:
                    s.add(deepsum(per_quality) == 0)
                else:
                    s.add(deepsum(per_quality) <= current_usage)

    for per_planet in true_machines_per_recipe.values():
        for per_recipe in per_planet.values():
            for per_quality in per_recipe.values():
                for per_machine_q in per_quality.values():
                    for per_quality_modules in per_machine_q.values():
                        for per_prod_modules in per_quality_modules.values():
                            for per_speed_modules in per_prod_modules.values():
                                for per_beacons in per_speed_modules.values():
                                    if isinstance(per_beacons, int):
                                        continue
                                    per_beacons.vtype = GRB.INTEGER

    s.update()

elif objective == "overhead":
    objective = overhead_cost + machine_cost * 10
    if len(goal) > 1:
        raise ValueError("Only one goal allowed for objective overhead")
    # s.add(overhead_cost >= goal_amount)
    s.add(overhead_cost >= goal[0]["amount"])
elif objective == "constrained":
    objective = -sum(goal_resources) + machine_cost / 1e6
    for planit in all_planets + ["space"]:
        s.add(speed_modules_used[planet] <= available_speed_modules[planet])
        s.add(quality_modules_used[planet] <= available_quality_modules[planet])
        s.add(prod_modules_used[planet] <= available_prod_modules[planet])
        s.add(beacons_used[planet] <= available_beacons[planet])
    for planet, planet_machines in machines.items():
        for machine, quality_amounts in planet_machines.items():
            for quality, amount in quality_amounts.items():
                s.add(amount <= available_machines[planet][machine][quality])
elif objective == "generate_cost_matrix":
    s.minimize(input_cost)
    result = defaultdict(lambda: defaultdict(lambda: [1e10 for _ in range(max_quality+1)]))
    for planet in all_planets + ["space"]:
        for item in compute_cost_for:
            for quality in range(max_quality+1):
                eq = s.add(resources[planet][item][quality] == 1)
                res = s.check()
                if is_satisfied(res):
                    m = s.model()
                    result[planet][item][quality] = get_float(m.evaluate(input_cost))
                    print(f"{planetName(planet)}: {itemName(item)} ({qualityName(quality, padding=False)}) costs {result[planet][item][quality]}")
                else:
                    print(f"{planetName(planet)}: {itemName(item)} ({qualityName(quality, padding=False)}) is unsolveable")
                s.remove(eq)
    print(json.dumps(result, indent=4))
    with open("cost_matrix.json", "w") as f:
        json.dump(result, f, indent=4)
    exit(0)
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


if is_satisfied(res):
    print("Solution found")
    print()
    m = s.model()
    # print(f"Producing {get_float(m.evaluate(goal_resource)):.2f} {goal_item} at quality {qualityName(goal_quality, padding=False)}")
    print("Producing:")
    for gr,g in zip(goal_resources, goal):
        print(f"  {get_float(m.evaluate(gr)):.2f} {itemName(g['item'])} at quality {qualityName(g['quality'], padding=False)}")
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

                                    effective_num_speed_modules = num_speed_modules + num_beacons * beacon.distribution_efficiency * 2

                                    speed_bonus = 1
                                    speed_bonus += speed_module.speed_bonus * effective_num_speed_modules
                                    speed_bonus += quality_module.speed_bonus * num_quality_modules
                                    speed_bonus += productivity_module.speed_bonus * num_productivity_modules
                                    speed_bonus = max(0.2, speed_bonus)

                                    productivity_bonus = 1
                                    productivity_bonus += recipe.productivity
                                    productivity_bonus += recipe.machine.productivity
                                    productivity_bonus += productivity_module.productivity_bonus * num_productivity_modules
                                    productivity_bonus += quality_module.productivity_bonus * num_quality_modules
                                    productivity_bonus += speed_module.productivity_bonus * effective_num_speed_modules
                                    productivity_bonus = max(1.0, productivity_bonus)

                                    recipe_amount = get_float(m[recipe_amounts[planet][ri][q][machine_q][num_quality_modules][num_productivity_modules][num_speed_modules][num_beacons]])
                                    machine_count = recipe_amount * recipe.crafting_time / recipe.machine.qspeed[machine_q] / speed_bonus
                                    if abs(machine_count) > eps:
                                        s = ""
                                        s+=("      ")
                                        s+=(f"{qualityName(q)}: {recipe_amount:6.2f}")
                                        prod_module_str = f"{itemName(productivity_module.name)}: {num_productivity_modules}"
                                        if num_productivity_modules == 0:
                                            prod_module_str = " " * len(prod_module_str)
                                        quality_module_str = f"{itemName(quality_module.name)}: {num_quality_modules}"
                                        if num_quality_modules == 0:
                                            quality_module_str = " " * len(quality_module_str)
                                        speed_module_str = f"{itemName(speed_module.name)}: {num_speed_modules}"
                                        if num_speed_modules == 0:
                                            speed_module_str = " " * len(speed_module_str)
                                        beacon_str = f"{beacon.name}: {num_beacons}"
                                        if num_beacons == 0:
                                            beacon_str = " " * len(beacon_str)
                                        s+=(f" ({prod_module_str}, {quality_module_str}, {speed_module_str}, {beacon_str})")
                                        s+=("  => ")
                                        if org_objective == "inputs_cost_matrix":
                                            # print(planet, ri, q, machine_q, num_quality_modules, num_productivity_modules, num_speed_modules, num_beacons)
                                            true_machine_count = get_float(m.evaluate(true_machines_per_recipe[planet][ri][q][machine_q][num_quality_modules][num_productivity_modules][num_speed_modules][num_beacons]))
                                            machine_cost = true_machine_count * cost_matrix[planet][recipe.machine.underlying_item][machine_q] 
                                            s+=(f"{machine_count:4.2f} ({true_machine_count}) {recipe.machine.name:}: ")
                                        else:
                                            s+=(f"{machine_count:4.2f} {recipe.machine.name:}: ")
                                        s+=" + ".join( [f"{recipe_amount*resource_amount:.2f}/s {itemName(resource)}" for resource, resource_amount in recipe.inputs.items()])
                                        s+=" -> "
                                        s+=" + ".join( [f"{recipe_amount*resource_amount*productivity_bonus:.2f}/s {itemName(resource)}" for resource, resource_amount in recipe.outputs.items()])
                                        
                                        machine_str.append(s)
                if machine_str:
                    print(f"    {recipe.name} in {recipe.machine.name} ({qualityName(machine_q, padding=False)}): ")
                    print("\n".join(machine_str))
            
    print()
    print(f"Total machines used ({get_float(m.evaluate(deepsum(machines))):.2f}):")
    for planet, planet_machines in machines.items():
        planet_str = []
        for machine, quality_amounts in planet_machines.items():
            machine_str = []
            for quality, amount in sorted(quality_amounts.items(), key=lambda x: x[0]):
                amount = get_float(m.evaluate(amount))
                if amount > eps:
                    machine_str.append(f"    {qualityName(quality)}: {amount:.2f}")
            if machine_str:
                planet_str.append(f"    {machine.name}: ")
                planet_str += machine_str
        if planet_str:
            print(f"  {planetName(planet)}: ")
            print("\n".join(planet_str))

    print()
    print(f"Total modules used ({get_float(m.evaluate(deepsum(speed_modules_used)+deepsum(quality_modules_used)+deepsum(prod_modules_used))):0.2f}):")
    for planet in all_planets + ["space"]:
        if abs(m.evaluate(speed_modules_used[planet] + quality_modules_used[planet] + prod_modules_used[planet] + beacons_used[planet])) < eps:
            continue
        print(f"  {planetName(planet)} ({get_float(m.evaluate(deepsum(speed_modules_used[planet])+deepsum(quality_modules_used[planet])+deepsum(prod_modules_used[planet]))):0.2f}): ")
        print(f"    {itemName(speed_module.name)}: {get_float(m.evaluate(speed_modules_used[planet])):.2f}")
        print(f"    {itemName(quality_module.name)}: {get_float(m.evaluate(quality_modules_used[planet])):.2f}")
        print(f"    {itemName(productivity_module.name)}: {get_float(m.evaluate(prod_modules_used[planet])):.2f}")
        print(f"    {beacon.name}: {get_float(m.evaluate(beacons_used[planet])):.2f}")

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
