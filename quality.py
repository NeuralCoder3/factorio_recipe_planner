# from mip import *
# iron = Integer('iron')


from z3 import *
import time

# s = Solver()
s = Optimize()

iron = Real('iron')
copper = Real('copper')

# iron_plates = Real('iron_plates')
# copper_wire = Real('copper_wire')

# green_circuits = Real('green_circuits')

v_iron = iron
v_copper = copper
# v_green_circuits = green_circuits

# intermediates/products are a priori zero -> nothing there
copper_wire = 0
iron_plates = 0
green_circuits = 0

# craft copper wire 
# from copper
# in assembler
copper_wire_assembler = Real('copper_wire_assembler')
copper_wire += 2*copper_wire_assembler
copper -= 1*copper_wire_assembler


# craft iron plates
# from iron
# in assembler
iron_plates_assembler = Real('iron_plates_assembler')
iron_plates += 1*iron_plates_assembler
iron -= 1*iron_plates_assembler


# craft green circuits
# from copper_wire and iron_plates
# in assembler
green_circuits_assembler = Real('green_circuits_assembler')
green_circuits += green_circuits_assembler
copper_wire -= 3*green_circuits_assembler
iron_plates -= 1*green_circuits_assembler

# all inputs are non-negative
s.add(copper >= 0)
s.add(iron >= 0)
# all intermediates are non-negative
s.add(copper_wire >= 0)
s.add(iron_plates >= 0)
s.add(green_circuits >= 0)


# we want green circuits
s.add(green_circuits >= 1)
s.minimize(iron + copper)

print("Solving...")
t0 = time.time()
res = s.check()
t1 = time.time()
print(f"Optimization took {t1-t0:.2f} seconds")

if res == sat:
    print("Solution found")
    print()
    m = s.model()
    print(f"Producing {m.evaluate(green_circuits)} green circuits")
    print(f"Iron: {m[v_iron]}, Copper: {m[v_copper]}")
    print(f"Copper wire crafted in assembler: {m[copper_wire_assembler]}")
    print(f"Iron plates crafted in assembler: {m[iron_plates_assembler]}")
    print(f"Green circuits crafted in assembler: {m[green_circuits_assembler]}")
    # print(f"Iron: {m[iron]}, Copper: {m[copper]}")
else:
    print("No solution found")
