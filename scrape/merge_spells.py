import json
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__)) 
MASTER = os.path.join(PROJECT_ROOT, "spells.json")

# usage: python merge.py file.json other.json third.json
merge_files = sys.argv[1:]

with open(MASTER, "r") as f:
    master = json.load(f)

others = []
for fp in merge_files:
    with open(fp, "r") as f:
        others.extend(json.load(f))

for a in others:
    for b in master:
        if (
            set([a["name"]] + a["alt_names"]).intersection(
                set([b["name"]] + b["alt_names"])
            )
        ):
            break
    else:
        print("Adding to master list:", a["name"])
        master.append(a)


master = sorted(master, key=lambda s: s["name"])

with open(os.path.join(PROJECT_ROOT, "merged_spells.json"), "w") as f:
    json.dump(master, f, indent=4)
