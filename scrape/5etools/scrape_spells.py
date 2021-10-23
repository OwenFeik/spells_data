import json
import os
import re
import requests
import traceback

from common import sub_tags

ROOT_URL = "https://5e.tools/data/spells/"
INDEX_URL = ROOT_URL + "index.json"

OUTDIR = "out"
OUTFILE = os.path.join(OUTDIR, "scraped.json")


# Map single character schools used by 5etools to full word schools used in
# spells.json
SCHOOL_MAPPING = {
    "A": "Abjuration",
    "C": "Conjuration",
    "D": "Divination",
    "E": "Enchantment",
    "I": "Illusion",
    "N": "Necromancy",
    "T": "Transmutation",
    "V": "Evocation"
}

# Map time units used by 5etools to those used in spells.json
CAST_TIME_MAPPING = {
    "bonus": "Bonus Action"
}

BULLET_POINT = "\u2022"

def parse_cast_time(spell):
    cast_time_info = spell["time"][0]
    n = cast_time_info["number"]
    unit = cast_time_info["unit"]

    if unit in CAST_TIME_MAPPING:
        unit = CAST_TIME_MAPPING[unit]
    else:
        unit = unit.capitalize()

    ret = f"{n} {unit}" 

    # 10 Minute -> 10 Minutes
    if n > 1:
        ret += "s"

    return ret

def parse_range(spell):
    rnge = spell["range"]
    dst = rnge.get("distance", {})

    if rnge["type"] == "point":
        if dst["type"] == "touch":
            return "Touch"
        elif dst["type"] == "self":
            return "Self"
        elif dst["type"] == "feet":
            return str(dst["amount"]) + " feet"
        elif dst["type"] == "miles":
            if dst["amount"] == 1:
                return "1 mile"
            else:
                return str(dst["amount"]) + " miles"
    elif rnge["type"] == "radius":
        if dst["type"] == "feet":
            return "Self (" + str(dst["amount"]) + "-foot radius)"
        elif dst["type"] == "miles":
            return "Self (" + str(dst["amount"]) + "-mile radius)"
    elif rnge["type"] == "sphere":
        return "Self (" + str(dst["amount"]) + "-foot-radius sphere)"
    elif rnge["type"] == "cone":
        if dst["type"] == "feet":
            return "Self (" + str(dst["amount"]) + "-foot cone)"
    elif rnge["type"] == "special":
        return "Special"
    
    print(f"Couldn't parse range for {spell['name']}: ", rnge)
    return ""

def parse_components(spell):
    comps = spell["components"]
    
    ret = ""
    for c in ["v", "s"]:
        if c in comps:
            if ret:
                ret += ", "
            ret += c.upper()

    if "m" in comps:
        if ret:
            ret += ", "

        if isinstance(comps["m"], dict):
            ret += "M (" + comps["m"]["text"] + ")"
        elif isinstance(comps["m"], str):
            ret += "M (" + comps["m"] + ")"
        else:
            print(
                "Failed to parse components for " + spell["name"] + ":",
                comps
            )

    if ret[-2:] == ", ":
        return ret[:-2]

    return ret

def parse_duration(spell):
    durn = spell["duration"][0]

    if durn["type"] == "timed":
        n = durn["duration"]["amount"]
        unit = durn["duration"]["type"]

        ret = f"{n} {unit}"
        if n > 1:
            ret += "s"
        
        if durn.get("concentration"):
            return "Concentration, up to " + ret
        return ret
    elif durn["type"] == "instant":
        return "Instantaneous"
    elif durn["type"] == "permanent":
        if "ends" in durn:
            if "dispel" in durn["ends"]:
                return "Until dispelled"
        return "Permanent"
    elif durn["type"] == "special":
        return "Special"

def pad_all_to_max_length(strings):
    l = max(len(s) for s in strings)
    return [s.ljust(l) for s in strings]

def parse_cell(cell):
    if isinstance(cell, str):
        return cell
    elif isinstance(cell, dict):
        if cell["type"] == "cell":
            r = cell["roll"]
            if "exact" in r:
                return str(r["exact"])
            
            ret = ""
            if "min" in r:
                ret += str(r["min"]) + "-"
            if "max" in r:
                if not ret:
                    ret = "-"
                ret += str(r["max"])
            return ret
    
    print("Failed to parse cell:", cell)
    raise ValueError

def format_table(entry):
    if "caption" in entry:
        ret = entry["caption"] + "\n"
    else:
        ret = ""

    rows = [entry["colLabels"]] + entry["rows"]
    cols = [
        pad_all_to_max_length([sub_tags(parse_cell(row[i])) for row in rows])
        for i in range(len(rows[0]))
    ]
    
    for i in range(len(cols)):
        row = [col[i] for col in cols]
        for j in range(len(row)):
            ret += row[j] + " "
        ret += "\n"
    
    return ret

def parse_entries(spell):
    ret = ""
    for e in spell["entries"]:
        if isinstance(e, str):
            ret += sub_tags(e)
        elif e["type"] == "table":
            ret += format_table(e)
        elif e["type"] == "entries":
            ret += e["name"] + ": " + parse_entries(e)
        elif e["type"] == "list":
            return "\n".join(BULLET_POINT + " " + sub_tags(i) for i in e["items"])
        elif e["type"] == "quote":
            continue
        else:
            print("Don't know how to handle type: " + e["type"])
            return ""

        ret += "\n\n"

    ret = re.sub(r"\n{3,}", "\n\n", ret)
    ret = re.sub(r"\n+$", "", ret)

    return ret

def parse_spell(spell):
    return {
        "name": spell["name"],
        "school": SCHOOL_MAPPING[spell["school"]],
        "level": spell["level"],
        "cast": parse_cast_time(spell),
        "range": parse_range(spell),
        "components": parse_components(spell),
        "duration": parse_duration(spell),
        "description": parse_entries(spell),
        "ritual": spell.get("meta", {}).get("ritual", False),
        "classes": [
            c["name"] for c in spell.get("classes", {}).get("fromClassList", [])
        ],
        "subclasses": [
            c["class"]["name"] + " (" + c["subclass"]["name"] + ")"
            for c in spell.get("classes", {}).get("fromSubclass", [])
        ],
        "alt_names": [spell["srd"]] if isinstance(spell.get("srd"), str) else []
    }

spells = []

if not os.path.isdir(OUTDIR):
    os.mkdir(OUTDIR)

index = requests.get(INDEX_URL).json()
for book in index:
    fp = f"out/{book}.json"
    print("Loading book", fp)

    if os.path.isfile(fp):
        with open(fp, "r") as f:
            data = json.load(f)
    else:
        data = requests.get(ROOT_URL + index[book]).json()
        with open(fp, "w") as f:
            json.dump(data, f, indent=4)

    for spell in data["spell"]:
        try:
            spells.append(parse_spell(spell))
            print("Parsed ", spell["name"])
        except:
            print("Failed to parse ", spell["name"])
            traceback.print_exc()
            exit()


with open(OUTFILE, "w") as f:
    json.dump(spells, f, indent=4)

print(f"Parsed {len(spells)} spells, saved to {OUTFILE}")
