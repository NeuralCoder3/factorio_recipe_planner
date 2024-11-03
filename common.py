from dataclasses import dataclass, field
from collections import defaultdict
from typing import Optional
import math


rarities = ["normal", "uncommon", "rare", "epic", "legendary"]
all_planets = ["nauvis", "fulgora", "vulcanus"]

fluids = set([
    "water", "crude_oil", "heavy_oil", "light_oil", "petroleum_gas", "sulfuric_acid", "lubricant",
    "steam", "molten_iron", "molten_copper", "lava", "holmium_solution", "electrolyte"
])

rocket_stack_sizes = {
    "coal": 500,
    "stone": 500,
    "iron_ore": 500,
    "copper_ore": 500,
    "iron_plate": 1000,
    "copper_plate": 1000,
    "steel_plate": 400,
    "solid_fuel": 1000,
    "plastic": 2000,
    "sulfur": 1000,
    "battery": 400,
    "explosives": 500,
    "carbon": 1000,
    "iron_gear_wheel": 1000,
    "iron_stick": 2000,
    "copper_cable": 4000,
    "electronic_circuit": 2000,
    "advanced_circuit": 1000,
    "processing_unit": 300,
    "engine_unit": 400,
    "electric_engine_unit": 400,
    "flying_robot_frame": 150,
    "low_density_structure": 200,
    "rocket_fuel": 100,
    #"rocket_part": 105,
    "uranium_235": 20,
    "uranium_238": 20,
    "uranium_fuel_cell": 10,
    "depleted_uranium_fuel_cell": 10,
    "nuclear_fuel": 10,
    "calcite": 500,
    "tungsten_ore": 100,
    "tungsten_carbide": 500,
    "tungsten_plate": 500,
    "holmium_ore": 500,
    "holmium_plate": 1000,
    "superconductor": 1000,
    "supercapacitor": 500,

    "speed_module": 50,
    "speed_module_2": 50,
    "speed_module_3": 50,
    "productivity_module": 50,
    "productivity_module_2": 50,
    "productivity_module_3": 50,
    "effeciency_module": 50,
    "effeciency_module_2": 50,
    "effeciency_module_3": 50,
    "quality_module": 50,
    "quality_module_2": 50,
    "quality_module_3": 50,

    "automation_science_pack": 1000,
    "logistic_science_pack": 1000,
    "military_science_pack": 1000,
    "chemical_science_pack": 1000,
    "production_science_pack": 1000,
    "utility_science_pack": 1000,
    "space_science_pack": 1000,
    "metallurgic_science_pack": 1000,
    "electromagnetic_science_pack": 1000,
    "agricultural_science_pack": 1000,
    "cryogenic_science_pack": 1000,
    "promethium_science_pack": 1000,
}

recycle_percentage = 0.25


def itemName(internal_name):
    # iron_ore => Iron Ore
    return " ".join([word.capitalize() for word in internal_name.split("_")])

def qualityName(quality, padding=True):
    max_len = max(len(r) for r in rarities)
    name = rarities[quality]
    if not padding:
        return name
    return " " * (max_len - len(name)) + name # + f" ({quality})"

def planetName(internal_name):
    return internal_name.capitalize()


@dataclass
class Module:
    name : str
    quality_bonus : float = 0
    speed_bonus : float = 0
    productivity_bonus : float = 0

@dataclass
class Beacon:
    name : str
    distribution_efficiency : float

@dataclass
class Machine:
    name : str
    module_slots : int
    speed : float
    qspeed : list[float] # the different crafting speeds for each quality level
    productivity : float = 0
    can_recycle : bool = True
    allowed_planets: list[str] = field(default_factory=lambda: ["space"] + all_planets)

@dataclass
class Recipe:
    machine : Machine
    inputs: dict[str, int]
    outputs: dict[str, int]
    name: str
    crafting_time : float = 1
    productivity : float = 0
    accepts_productivity : bool = True
    accepts_quality : bool = True
    accepts_quality_module : bool = True
    can_recycle: bool = True
    allowed_planets: list[str] = field(default_factory=lambda: all_planets + (["space"] if allow_space_crafting else []))
    forced_quality: Optional[int] = None # the base quality of the recipe is forced
    forced_input_quality: dict[str, int] = field(default_factory=dict)
    forced_output_quality: dict[str, int] = field(default_factory=dict)
    forced_input_planet: Optional[str] = None
    forced_output_planet: Optional[str] = None
    
#region Modules
speed_modules = [[]] + [
    [
        Module(
            name=f"Speed Module {level+1} ({qualityName(q, padding=False)})",
            quality_bonus=[-0.01, -0.015, -0.025][level],
            speed_bonus=[0.2, 0.3, 0.5][level] * [1, 1.3, 1.6, 1.9, 2.5][q],
        ) for q in range(len(rarities))
    ] for level in range(3)
]
productivity_modules = [[]] + [
    [
        Module(
            name=f"Productivity Module {level+1} ({qualityName(q, padding=False)})",
            productivity_bonus=math.floor([0.04, 0.06, 0.1][level] * [1, 1.3, 1.6, 1.9, 2.5][q] * 100) / 100,
            speed_bonus=[-0.05, -0.10, -0.15][level],
        ) for q in range(len(rarities))
    ] for level in range(3)
]
quality_modules = [[]] + [
    [
        Module(
            name=f"Quality Module {level+1} ({qualityName(q, padding=False)})",
            quality_bonus=[0.01, 0.02, 0.025][level] * [1, 1.3, 1.6, 1.9, 2.5][q],
            speed_bonus=[-0.05, -0.10, -0.15][level],
        ) for q in range(len(rarities))
    ] for level in range(3)
]
beacons = [
    Beacon(
        name=f"Beacon ({qualityName(q, padding=False)})",
        distribution_efficiency=[1.5, 1.7, 1.9, 2.1, 2.5][q]
    ) for q in range(len(rarities))
]
#endregion
    
#region Machines
miner = Machine(
    "Miner",
    module_slots=3,
    speed=0.5,
    qspeed=[0.5, 0.5, 0.5, 0.5, 0.5],
    can_recycle=False
)

big_miner = Machine(
    "Big Miner",
    module_slots=4,
    speed=2.5,
    qspeed=[2.5, 2.5, 2.5, 2.5, 2.5],
    can_recycle=False
)

smelter = Machine(
    "Smelter",
    module_slots=2,
    speed=2,
    qspeed=[2, 2.6, 3.2, 3.8, 5],
    can_recycle=False
)
    
assembler = Machine(
    "Assembler", 
    module_slots=4, 
    speed=1.25,
    qspeed=[1.25, 1.625, 2, 2.375, 3.125],
)

oil_refinery = Machine(
    "Oil Refinery",
    module_slots=3,
    speed=1,
    qspeed=[1, 1.3, 1.6, 1.9, 2.5],
    can_recycle=False
)

chemical_plant = Machine(
    "Chemical Plant",
    module_slots=3,
    speed=1,
    qspeed=[1, 1.3, 1.6, 1.9, 2.5],
    can_recycle=False
)

recycler = Machine(
    "Recycler",
    module_slots=4,
    speed=0.5,
    qspeed=[0.5, 0.65, 0.8, 0.95, 1.25],
    can_recycle=False
)

foundry = Machine(
    "Foundry",
    module_slots=4,
    speed=4,
    qspeed=[4, 5.2, 6.4, 7.6, 10],
    productivity=0.5,
    can_recycle=False
)

electromagnetic_plant = Machine(
    "Electromagnetic Plant",
    module_slots=5,
    speed=2,
    qspeed=[2, 2.6, 3.2, 3.8, 5],
    productivity=0.5
)

rocket_silo = Machine(
    "Rocket Silo",
    module_slots=4,
    speed=1,
    qspeed=[1, 1.3, 1.6, 1.9, 2.5],
    allowed_planets=all_planets,
    can_recycle=False
)

rocket = Machine(
    "Rocket",
    module_slots=0,
    speed=1,
    qspeed=[1, 1, 1, 1, 1],
    can_recycle=False
)

drop_pod = Machine(
    "Drop Pod",
    module_slots=0,
    speed=1,
    qspeed=[1, 1, 1, 1, 1],
    can_recycle=False
)

dummy = Machine(
    "Dummy Converter",
    module_slots=0,
    speed=100,
    qspeed=[1e3, 1e3, 1e3, 1e3, 1e3],
    can_recycle=False
)
#endregion

exclude_machines = [
    # foundry
]
allow_recycling = recycler not in exclude_machines


recipes : list[Recipe] = []

def define_recipes():
    global recipes

    #region recipes for all miners
    for machine in [miner, big_miner]:
        recipes += [
            Recipe(
                name="Mine Copper",
                machine=machine,
                inputs={"copper_ore_vein": 1},
                outputs={"copper_ore": 1},
                productivity=item_productivity["mining"],
                crafting_time=1
            ),
            Recipe(
                name="Mine Iron",
                machine=machine,
                inputs={"iron_ore_vein": 1},
                outputs={"iron_ore": 1},
                productivity=item_productivity["mining"],
                crafting_time=1
            ),
            Recipe(
                name="Mine Coal",
                machine=machine,
                inputs={"coal_vein": 1},
                outputs={"coal": 1},
                productivity=item_productivity["mining"],
                crafting_time=1
            ),
            Recipe(
                name="Mine Calcite",
                machine=machine,
                inputs={"calcite_vein": 1},
                outputs={"calcite": 1},
                productivity=item_productivity["mining"],
                crafting_time=1
            ),
            Recipe(
                name="Mine Scrap",
                machine=machine,
                inputs={"scrap_vein": 1},
                outputs={"scrap": 1},
                productivity=item_productivity["mining"],
                crafting_time=1
            ),
        ]
    #endregion

    recipes += [
        #region special mining/"smelting" recipes
        Recipe(
            name="Mine Tungsten",
            machine=big_miner,
            inputs={"tungsten_ore_vein": 1},
            outputs={"tungsten_ore": 1},
            productivity=item_productivity["mining"],
            crafting_time=0.2
        ),
        Recipe(
            name="Recycle Scrap",
            machine=recycler,
            inputs={"scrap": 1},
            outputs={
                "processing_unit": 0.02,
                "advanced_circuit": 0.03,
                "low_density_structure": 0.01,
                "solid_fuel": 0.07,
                "steel_plate": 0.04,
                "concrete": 0.06,
                "battery": 0.04,
                "ice": 0.05,
                "stone": 0.04,
                "holmium_ore": 0.01,
                "iron_gear_wheel": 0.2,
                "copper_cable": 0.03,
            },
            productivity=item_productivity["scrap"],
            crafting_time=0.2
        ),
        #endregion

        #region smelting recipes
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
            name="Steel Smelting",
            machine=smelter,
            inputs={"iron_plate": 5},
            outputs={"steel_plate": 1},
            productivity=item_productivity["steel_plate"],
            crafting_time=16
        ),
        #endregion

        #region foundry recipes
        Recipe(
            name="Melt Copper",
            machine=foundry,
            inputs={"copper_ore": 50, "calcite": 1},
            outputs={"molten_copper": 500},
            crafting_time=32
        ),
        Recipe(
            name="Melt Copper From Lava",
            machine=foundry,
            inputs={"lava": 50, "calcite": 1},
            outputs={"molten_copper": 250, "stone": 20},
            crafting_time=16
        ),
        Recipe(
            name="Melt Iron",
            machine=foundry,
            inputs={"iron_ore": 500, "calcite": 1},
            outputs={"molten_iron": 500},
            crafting_time=32
        ),
        Recipe(
            name="Melt Iron From Lava",
            machine=foundry,
            inputs={"lava": 50, "calcite": 1},
            outputs={"molten_iron": 250, "stone": 20},
            crafting_time=16
        ),
        Recipe(
            name="Cast Iron",
            machine=foundry,
            inputs={"molten_iron": 20},
            outputs={"iron_plate": 2},
            crafting_time=3.2
        ),
        Recipe(
            name="Cast Copper",
            machine=foundry,
            inputs={"molten_copper": 20},
            outputs={"copper_plate": 2},
            crafting_time=3.2
        ),
        Recipe(
            name="Cast Steel",
            machine=foundry,
            inputs={"molten_iron": 30},
            outputs={"steel_plate": 1},
            productivity=item_productivity["steel_plate"],
            crafting_time=3.2
        ),
        Recipe(
            name="Cast Iron Gear Wheel",
            machine=foundry,
            inputs={"molten_iron": 10},
            outputs={"iron_gear_wheel": 1},
            crafting_time=1
        ),
        Recipe(
            name="Cast Iron Stick",
            machine=foundry,
            inputs={"molten_iron": 20},
            outputs={"iron_stick": 4},
            crafting_time=1
        ),
        Recipe(
            name="Cast Low Density Structure",
            machine=foundry,
            inputs={"molten_copper": 80, "molten_iron": 250, "plastic": 5},
            outputs={"low_density_structure": 1},
            productivity=item_productivity["low_density_structure"],
            crafting_time=15
        ),
        Recipe(
            name="Concrete From Molten Iron",
            machine=foundry,
            inputs={"stone_brick": 5, "molten_iron": 20, "water": 100},
            outputs={"concrete": 10},
            crafting_time=10
        ),
        Recipe(
            name="Cast Copper Wire",
            machine=foundry,
            inputs={"molten_copper": 5},
            outputs={"copper_cable": 2},
            crafting_time=1
        ),
        Recipe(
            name="Tungsten Plate",
            machine=foundry,
            inputs={"tungsten_ore": 4, "molten_iron": 10},
            outputs={"tungsten_plate": 1},
            crafting_time=10
        ),
        Recipe(
            name="Holmium Plate",
            machine=foundry,
            inputs={"holmium_solution": 20},
            outputs={"tungsten_plate": 1},
            crafting_time=1
        ),
        Recipe(
            name="Metallurgic Science Pack",
            machine=foundry,
            inputs={"tungsten_carbide": 3, "tungsten_plate": 2, "molten_copper": 200},
            outputs={"metallurgic_science_pack" : 1},
            crafting_time=1,
            allowed_planets=["vulcanus"]
        ),
        #endregion

        #region refinery recipes
        Recipe(
            name="Basic Oil Processing",
            machine=oil_refinery,
            inputs={"crude_oil": 100},
            outputs={"petroleum_gas": 45},
            crafting_time=5
        ),
        Recipe(
            name="Advanced Oil Processing",
            machine=oil_refinery,
            inputs={"crude_oil": 100, "water": 50},
            outputs={"heavy_oil": 25, "light_oil": 45, "petroleum_gas": 55},
            crafting_time=5
        ),
        Recipe(
            name="Simple Coal Liquefaction",
            machine=oil_refinery,
            inputs={"coal": 10, "calcite": 2, "sulfuric_acid": 25},
            outputs={"heavy_oil": 50},
            crafting_time=5
        ),
        Recipe(
            name="Coal Liquefaction",
            machine=oil_refinery,
            inputs={"coal": 10, "heavy_oil": 25, "steam": 50},
            outputs={"heavy_oil": 90, "light_oil": 20, "petroleum_gas": 10},
            crafting_time=5
        ),
        #endregion

        #region chemistry recipes
        Recipe(
            name="Heavy Oil Cracking To Light Oil",
            machine=chemical_plant,
            inputs={"heavy_oil": 40, "water": 30},
            outputs={"light_oil": 30},
            crafting_time=2
        ),
        Recipe(
            name="Light Oil Cracking To Petroleum Gas",
            machine=chemical_plant,
            inputs={"light_oil": 30, "water": 30},
            outputs={"petroleum_gas": 20},
            crafting_time=2
        ),
        Recipe(
            name="Solid Fuel From Heavy Oil",
            machine=chemical_plant,
            inputs={"heavy_oil": 20},
            outputs={"solid_fuel": 1},
            crafting_time=1
        ),
        Recipe(
            name="Solid Fuel From Light Oil",
            machine=chemical_plant,
            inputs={"light_oil": 10},
            outputs={"solid_fuel": 1},
            crafting_time=1
        ),
        Recipe(
            name="Solid Fuel From Petroleum Gas",
            machine=chemical_plant,
            inputs={"petroleum_gas": 20},
            outputs={"solid_fuel": 1},
            crafting_time=1
        ),
        Recipe(
            name="Lubricant",
            machine=chemical_plant,
            inputs={"heavy_oil": 10},
            outputs={"lubricant": 10},
            crafting_time=1
        ),
        Recipe(
            name="Plastic",
            machine=chemical_plant,
            inputs={"coal": 1, "petroleum_gas": 20},
            outputs={"plastic": 2},
            productivity=item_productivity["plastic"],
            crafting_time=1
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
            name="Battery",
            machine=chemical_plant,
            inputs={"iron_plate": 1, "copper_plate": 1, "sulfuric_acid": 20},
            outputs={"battery": 1},
            crafting_time=4
        ),
        Recipe(
            name="Explosives",
            machine=chemical_plant,
            inputs={"coal": 1, "sulfur": 1, "water": 10},
            outputs={"explosives": 2},
            crafting_time=4
        ),
        Recipe(
            name="Carbon",
            machine=chemical_plant,
            inputs={"coal": 2, "sulfuric_acid": 20},
            outputs={"carbon": 1},
            crafting_time=1
        ),
        Recipe(
            name="Acid Neutralization",
            machine=chemical_plant,
            inputs={"sulfuric_acid": 1000, "calcite": 1},
            outputs={"steam": 10000},
            allowed_planets=["vulcanus"],
            crafting_time=5
        ),
        Recipe(
            name="Steam Condensation",
            machine=chemical_plant,
            inputs={"steam": 1000},
            outputs={"water": 90},
            crafting_time=1
        ),
        Recipe(
            name="Ice melting",
            machine=chemical_plant,
            inputs={"ice": 1},
            outputs={"water": 20},
            crafting_time=1
        ),
        Recipe(
            name="Holmium Solution",
            machine=chemical_plant,
            inputs={"holmium_ore": 2, "water": 10, "stone": 1},
            outputs={"holmium_solution": 100},
            crafting_time=10
        ),
        #endregion

        #region assembler recipes
        Recipe(
            name="Low Density Structure",
            machine=assembler,
            inputs={"copper_plate": 20, "steel_plate": 2, "plastic": 5},
            outputs={"low_density_structure": 1},
            productivity=item_productivity["low_density_structure"],
            crafting_time=15
        ),
        Recipe(
            name="Iron Gear Wheel",
            machine=assembler,
            inputs={"iron_plate": 2},
            outputs={"iron_gear_wheel": 1},
            crafting_time=0.5
        ),
        Recipe(
            name="Rocket Fuel",
            machine=assembler,
            inputs={"solid_fuel": 10, "light_oil": 10},
            outputs={"rocket_fuel": 1},
            productivity=item_productivity["rocket_fuel"],
            crafting_time=15
        ),
        #endregion

        #region electromagnetic plant recipes
        Recipe(
            name="Superconductor",
            machine=electromagnetic_plant,
            inputs={"copper_plate": 1, "plastic": 1, "holmium_plate": 1, "light_oil": 5},
            outputs={"superconductor": 2},
            crafting_time=5
        ),
        Recipe(
            name="Electrolyte",
            machine=electromagnetic_plant,
            inputs={"stone": 1, "heavy_oil": 10, "holmium_solution": 10},
            outputs={"electrolyte": 10},
            crafting_time=5
        ),
        Recipe(
            name="Supercapacitor",
            machine=electromagnetic_plant,
            inputs={"battery": 1, "electronic_circuit": 4, "holmium_plate": 2, "superconductor": 2, "electrolyte": 10},
            outputs={"supercapacitor": 1},
            crafting_time=10
        ),
        Recipe(
            name="Electromagnetic Science Pack",
            machine=electromagnetic_plant,
            inputs={"supercapacitor": 1, "accumulator": 1, "electrolyte": 25, "holmium_solution": 25},
            outputs={"electromagnetic_science_pack" : 1},
            crafting_time=10,
            allowed_planets=["fulgora"]
        ),
        #endregion

        #region Rocket Silo recipes
        Recipe(
            name="Rocket Part",
            machine=rocket_silo,
            inputs={"low_density_structure": 1, "rocket_fuel": 1, "processing_unit": 1},
            outputs={"rocket_part": 1},
            forced_quality=0,
            crafting_time=3,
            accepts_quality=False
        ),
        #endregion
    ]

    #region recipes for both assembler and eletromagnetic plant
    for machine in [assembler, electromagnetic_plant]:
        recipes += [
            Recipe(
                name="Copper Cable",
                machine=machine,
                inputs={"copper_plate": 1},
                outputs={"copper_cable": 2},
                crafting_time=0.5
            ),
            Recipe(
                name="Electronic Circuits",
                machine=machine,
                inputs={"copper_cable": 3, "iron_plate": 1},
                outputs={"electronic_circuit": 1},
                crafting_time=0.5
            ),
            Recipe(
                name="Advanced Circuits",
                machine=machine,
                inputs={"copper_cable": 4, "plastic": 2, "electronic_circuit": 2},
                outputs={"advanced_circuit": 1},
                crafting_time=6
            ),
            Recipe(
                name="Processing Unit",
                machine=machine,
                inputs={"advanced_circuit": 2, "electronic_circuit": 20, "sulfuric_acid": 5},
                outputs={"processing_unit": 1},
                productivity=item_productivity["processing_unit"],
                crafting_time=10
            ),
            Recipe(
                name="Quality Module",
                machine=machine,
                inputs={"advanced_circuit": 5, "electronic_circuit": 5},
                outputs={"quality_module": 1},
                crafting_time=15
            ),
            Recipe(
                name="Quality Module 2",
                machine=machine,
                inputs={"advanced_circuit": 5, "processing_unit": 5, "quality_module": 4},
                outputs={"quality_module_2": 1},
                crafting_time=30
            ),
            Recipe(
                name="Quality Module 3",
                machine=machine,
                inputs={"advanced_circuit": 5, "processing_unit": 5, "quality_module_2": 4, "superconductor": 1},
                outputs={"quality_module_3": 1},
                crafting_time=60
            ),
        ]
    #endregion

    #region recipes for both assembler and foundry
    for machine in [assembler, electromagnetic_plant]:
        recipes += [
            Recipe(
                name="Holmium Plate",
                machine=machine,
                inputs={"holmium_solution": 20},
                outputs={"holmium_plate": 1},
                crafting_time=1
            ),
        ]
    #endregion

    recipes = [r for r in recipes if r.machine not in exclude_machines]

    global recycle_recipes
    recycle_recipes = []
    recycle_map = {}
    recipe_count = len(recipes)
    if allow_recycling:
        i = 0
        for ri, recipe in enumerate(recipes):
            if not recipe.can_recycle:
                continue
            if not recipe.machine.can_recycle:
                continue
            if len(recipe.outputs) > 1:
                continue
            if all(inp in fluids for inp in recipe.inputs):
                continue
            recycle_outputs = {}
            for inp, amount in recipe.inputs.items():
                if inp in fluids:
                    continue
                recycle_outputs[inp] = amount * recycle_percentage
            recycle_recipes.append(
                Recipe(
                    name=f"Recycle {recipe.name}",
                    machine=recycler,
                    inputs=recipe.outputs,
                    outputs=recycle_outputs,
                    crafting_time=recipe.crafting_time / 8,
                    accepts_productivity=False,
                )
            )
            recycle_map[ri] = i+recipe_count
            i+=1

    science_dummy_recipes = [
        Recipe(
            name=f"Convert {itemName(s + '_pack')} to {itemName(s)}",
            machine=dummy,
            inputs={s + "_pack": 1},
            outputs={s: 1},
            crafting_time=1
        )
        for s in science_to_consider]


    global space_travel_recipes
    space_travel_recipes = []
    if "space" not in exclude_planets:
        for item, stack_size in rocket_stack_sizes.items():
            space_travel_recipes.append(
                Recipe(
                    name=f"Send {itemName(item)} to Space",
                    machine=rocket,
                    inputs={"rocket_part": 50, item: stack_size},
                    outputs={item: stack_size},
                    forced_input_quality={"rocket_part": 0},
                    forced_output_planet="space",
                    allowed_planets=all_planets,
                    accepts_productivity=False,
                    accepts_quality_module=False,
                    crafting_time=30,
                    can_recycle=False
                )
            )
        for item, stack_size in rocket_stack_sizes.items():
            space_travel_recipes.append(
                Recipe(
                    name=f"Recieve {itemName(item)} from Space",
                    machine=drop_pod,
                    inputs={item: stack_size},
                    outputs={item: stack_size},
                    forced_input_planet="space",
                    allowed_planets=all_planets,
                    accepts_productivity=False,
                    accepts_quality_module=False,
                    crafting_time=1,
                    can_recycle=False
                )
            )
    
    global all_recipes
    all_recipes = recipes + recycle_recipes + science_dummy_recipes + space_travel_recipes
    # all_recipes = recipes + recycle_recipes


#region Configuration

# objective = "overhead"
objective = "inputs"
# objective = "constrained"

# goal_item = "electronic_circuit"
# goal_quality = 2
# goal_item = "advanced_circuit"
# goal_quality = 2
# goal_item = "processing_unit"
# goal_quality = 2

goal_item = "quality_module_3"
goal_planet = "vulcanus"
goal_quality = 2
goal_amount = 1

max_quality = 2
# max_quality = len(rarities)-1

# module level is one indexed
quality_module = quality_modules[3][2]
productivity_module = productivity_modules[2][2]
speed_module = speed_modules[3][2]
beacon = beacons[2]

beacon_sharedness = 1 / 8 # every beacon is assumed to affect 8 machines
max_beacons_per_machine = 4

item_productivity = {
    # productivity research (e.g. steel)
    "low_density_structure": 0.2,
    "steel_plate": 0.2,
    "processing_unit": 0.1,
    "plastic": 0.0,
    "rocket_fuel": 0.0,
    "asteroids": 0.0,
    "scrap": 0.3,
    "mining": 0.3,
}

allow_space_crafting = False
reduce_space_travel = True



# only needed for constrained mode
available_machines = defaultdict(lambda: [1e5, 0, 0, 0, 0])
available_machines.update({
    "Miner": [1e10, 0, 0, 0, 0],
    "Smelter": [330, 735, 142, 0, 0],
    "Assembler": [340, 175, 74, 0, 0],
    "Oil Refinery": [100, 0, 0, 0, 0],
    "Chemical Plant": [1000, 20, 20, 0, 0],
    "Recycler": [35, 20, 1, 0, 0],
    "Foundry": [200, 0, 0, 0, 0],
    "Electromagnetic Plant": [10, 5, 0, 0, 0],
    "Rocket Silo": [100, 0, 0, 0, 0],

    #"Rocket": [1e5, 0, 0, 0, 0],
    #"Drop Pod": [1e5, 0, 0, 0, 0],
    #"Dummy Converter": [1e5, 0, 0, 0, 0],
})

available_beacons = 50
available_speed_modules = 350
available_quality_modules = 1300
available_prod_modules = 1000

science_to_consider = [
    "automation_science",
    "logistic_science",
    "military_science",
    "chemical_science",
    "production_science",
    "utility_science",
    "space_science",
    "metallurgic_science",
    "electromagnetic_science",
    #"agricultural_science",
    #"cryogenic_science",
    #"promethium_science",
]


exclude_planets = [
    # "space",
    # "nauvis",
    # "fulgora",
    # "vulcanus",
]

# planet -> item -> cost scaling factor
inputs_per_planet = {
    "space": {
        "metallic_asteroid": 10,
        "carbonic_asteroid": 10,
        "oxide_asteroid": 20,
    },
    "nauvis": {
        "iron_ore_vein": 1,
        "copper_ore_vein": 1,
        "coal_vein": 1,
        "crude_oil": 0.01,
        "water": 0,
    },
    "fulgora": {
        "scrap_vein": 1,
        "heavy_oil": 0,
    },
    "vulcanus": {
        "lava": 0,
        "calcite_vein": 1,
        "coal_vein": 1,
        "tungsten_ore_vein": 1,
        "sulfuric_acid": 0.001,
    }
}

#endregion

define_recipes()