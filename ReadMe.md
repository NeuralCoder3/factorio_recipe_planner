# Factorio Recipe Planner

In [Factorio 1](https://www.factorio.com/), recipes were quite simple.
One had factories that produces a result.
If we needed one, we had at most two variants and at most productivity modules to create more or speed to create faster.
There are two cycles (coal liquification and kovarex).
Other than that, recipes are not too complicated and can be solved easily as linear systems with lp-solvers.

There are many tools available such as [Helmod](https://mods.factorio.com/mod/helmod) or [KirkMcDonald Calc](https://kirkmcdonald.github.io/calc.html).

With [Factorio Space Age](https://www.factorio.com/space-age/content), this got more complicated:
Each item has qualities, you can create directly melt iron to skip processing steps, there are more machines with additional productivity, you can recycle items to get a few resources back, ...

The most complicated (to understand and solve) aspect is quality:
With quality modules, you get a certain percentage of higher quality items (there are multiple stages of quality).
Additionally, you can recycle items to get a new roll to get higher items or even upgrade during the recycling.

You want high-quality items as they have nice bonuses.

Now you have to carefully think about when to use quality and productivity.
Early quality allows for easier crafting of high-quality intermediate and a fast climb in quality levels.
But productivity creates more quality items or items to try with.

Now, we want to see what the optimal factory is to create a certain quality item.
For this, we can optimize for instance for input resources such as ores.

## What this tool does

We create a plan of factories and which modules to use.
Our assumptions are:
- Each machine of one type has the same modules
  This makes the building easier and works guaranteed the same as in our model (not necessarily true with ration modules)
- We just look at how many products are created (for now)

An example plan looks like this:
```
Producing 1.00 green_circuit at quality rare
Objective (inputs): 138.90

Resources:
  Iron Ore: 
       normal: 63.26
  Copper Ore: 
       normal: 75.64

Machines:
  Copper Smelting crafted in Smelter: 
       normal:  75.64 (Productivity: 2.00, Quality: 0.00)
  Iron Smelting crafted in Smelter: 
       normal:  63.26 (Productivity: 0.00, Quality: 2.00)
  Copper Wire crafted in Assembler: 
       normal:  84.72 (Productivity: 2.00, Quality: 2.00)
  Green Circuits crafted in Assembler: 
       normal:  60.48 (Productivity: 0.00, Quality: 4.00)
     uncommon:   2.53 (Productivity: 0.00, Quality: 4.00)
         rare:   0.25 (Productivity: 4.00, Quality: -0.00)

Left over resources:
  Iron Ore: 
  Copper Ore: 
  Copper Plate: 
  Iron Plate: 
  Copper Wire: 
  Green Circuit: 
       normal: 55.15
     uncommon: 7.17
         rare: 1.00
```

## Modelling

We model the input resources as variables.
Additionally, we have variables for each factory how many times we use the recipe (roughly how many factories one would build (modulo crafting time)).

For each item, we build a formula as sum of producers of this item minus the usages of the item. That is, applying the recipes with the (variable) amounts.

Each input and product (e.g. intermediates) has to be non-negative in the end as we can not craft from thin air.
Our goal is that a specific resource is produced (has count at least 1).
We can optimize for overhead that is produced or input ingredients used during production.

For each recipe, we ensure that only a positive amount is crafted.
For quality, we produce the corresponding amount of higher quality items for the used modules (module percentage for quality+1 and /10 for each consecutive level).
Productivity just produces more products in general.

The modules can at most add up to the available module slots and are integer variables.

Fluids need special consideration as they can not have any quality.
They are always produces as "normal" fluids.
Any fluid used in a recipe is ignored for quality constraints.

We showcase a nice overloading strategy to allow an easy switch between `z3`, `python-mip`, and `gurobi` (which is the fastest and as only one able to solve with variable productivity and quality modules).

A special hurdle is the combination of quality and productivity (which can be necessary in certain circumstances).
We get `output * recipe_amount * (1+prod_modules*prod) * (quality_modules*quality)` items.
However, this is a cubic constraint. We can encode the constraint as a quadratic one using auxiliary variables for one of the multiplications.