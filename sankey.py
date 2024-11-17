import os
import sys
import json
import plotly.graph_objects as go

if len(sys.argv) != 2:
    print(f"Usage: python {sys.argv[0]} filename.json")
    sys.exit(1)
filename = sys.argv[1]
with open(filename, "r") as f:
    data = json.load(f)
    
items = set()
recipes = set()
for planet in data["machines"]:
    for recipe in data["machines"][planet]:
        items.update(recipe["input"].keys())
        items.update(recipe["output"].keys())
        recipes.add(recipe["recipe"])
        
# map from item to index
items = {item: i for i, item in enumerate(items)}
recipes = {recipe: len(items)+i for i, recipe in enumerate(recipes)}

node_labels = [ 
    name for name, idx in 
    (list(sorted(items.items(), key=lambda x: x[1])) +
    list(sorted(recipes.items(), key=lambda x: x[1]))) 
]

lightblue = 'rgba(173, 216, 230, 0.9)'
lightorange = 'rgba(251, 192, 147, 0.9)'
lightblue2 = 'rgba(173, 216, 230, 0.7)'
lightorange2 = 'rgba(251, 192, 147, 0.7)'
node_colors = \
    [lightblue for _ in items] + \
    [lightorange for _ in recipes]

sources = []
targets = []
values = []
labels = []
colors = []
for planet in data["machines"]:
    for recipe in data["machines"][planet]:
        machine_count = recipe["true_machine_count"]
        machine_quality = recipe["machine_quality"]
        quality = recipe["quality"]
        machine = recipe["machine"]
        name = recipe["recipe"]
        
        label = f"{machine_count:.2f} {machine_quality} {machine} on {quality} ({name})"
        # TODO: modules
        
        for item, count in recipe["input"].items():
            sources.append(items[item])
            targets.append(recipes[name])
            values.append(count)
            labels.append(label)
            colors.append(lightblue2)
        for item, count in recipe["output"].items():
            sources.append(recipes[name])
            targets.append(items[item])
            values.append(count)
            labels.append(label) 
            colors.append(lightorange2)

fig = go.Figure(data=[go.Sankey(
    valueformat = ".0f",
    valuesuffix = "Item/s",
    node = dict(
      pad = 15,
      thickness = 15,
      line = dict(color = "black", width = 0.5),
      label = node_labels,
      color = node_colors
    ),
    link = dict(
        source = sources,
        target = targets,
        value = values,
        label = labels,
        color = colors,
))])

title = ""
for goal in data["goal"]:
    title += f"{goal['quantity']:.2f} {goal['item']} at quality {goal['quality']} {'on '+goal['planet'] if goal['planet'] else ''}<br>"

fig.update_layout(
    title_text=title,
    font_size=10
)
fig.show()