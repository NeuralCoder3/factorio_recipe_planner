Recipes:
- 1 Iron Ore -> 3.2s -> 1 Iron Plate 
- 1 Copper Ore -> 3.2s -> 1 Copper Plate 
- 1 Copper -> 0.5s -> 2 Copper Wire
- 1 Iron Plate, 3 Copper Wire -> 0.5s -> 1 Green Circuit
- 2 Plastic, 4 Copper Wire, 2 Green Circuit -> 6s -> 1 Red Circuit

Chemical Plant:
- 1 Coal, 20 Petroleum -> 1s -> 2 Plastic

ElectroMagnetic Recipes:
- Modules
- Circuits
- Copper Wire
- Solar, Accumulator

Foundry Recipes:
- 1 Calcite, 500 Lava -> 16s -> 10 Stone, 250 Molten Iron
- 1 Calcite, 50 Iron -> 32s -> 500 Molten Iron
- 20 Molten Iron -> 3.2s -> 2 Iron Plate
- 10 Molten Iron -> 1s -> 1 Iron Gear

Machines:
- Furnace 
    - 2 Slots
    - 2 Crafting Speed (2.6, 3.2, 3.8, 5)
- Assembler
    - 4 Slots
    - 1.25 Crafting Speed (1.625, 2, 2.375, 3.125)
- Foundry
    - 4 Slots
    - 4 Crafting Speed (5.2, 6.4, 7.6, 10)
    - 50% Producitivity
- ElectroMagnetic
    - 5 Slots
    - 2 Crafting Speed (2.6, 3.2, 3.8, 5)
    - 50% Producitivity
- Recycler
    - 4 Slots
    - 0.5 Crafting Speed (0.65, 0.8, 0.95, 1.25)
- Chemical Plant:
    - 3 Slots
    - 1 Crafting Speed (1.3, 1.6, 1.9, 2.5)

Modules:
- Productivity 1
    - Speed -5%
    - Prod 4% (5, 6, 7, 10)
- Productivity 2
    - Speed -10%
    - Prod 6% (7, 9, 11, 15)
- Productivity 3
    - Speed -15%
    - Prod 10% (13, 16, 19, 25)
- Quality 1
    - Speed -5%
    - Quality 1% (1.3, 1.6, 1.9, 2.5)
- Quality 2
    - Speed -5%
    - Quality 2% (2.6, 3.2, 3.8, 5)
- Quality 3
    - Speed -5%
    - Quality 2.5% (3.2, 4, 4.7, 6.2)


quality:
- sum of percent for q+1
- percent/10 for q+2
- percent/100 for q+3 
- ...


first: no modules
then only modules 2, no quality


