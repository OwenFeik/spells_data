import json
import re

with open('temp.json', 'r') as f:
    creatures = json.load(f)

def sub_tags(string):
    return re.sub(
        r'{@\w+ ([\w\s ]+)(\|phb)?}',
        r'\1',
        string,
        flags=re.MULTILINE
    )

out = []
for c in creatures:
    # d = {k: c.get(k) for k in
    #     [
    #         "name",
    #         "size",
    #         "type",
    #         "str",
    #         "dex",
    #         "con",
    #         "int",
    #         "wis",
    #         "cha",
    #         "languages",
    #         "cr",
    #         "speed",
    #         "save",
    #         "skill",
    #         "senses"
    #     ]
    # }
    d = {}


    text = ""
    for ac in c["ac"]:
        if text:
            text += "; "

        if type(ac) is int:
            text += str(ac)
            continue

        text += str(ac.get("ac"))

        if "condition" in ac:
            text += " (" + sub_tags(ac["condition"]) + ")"

        if "from" in ac:
            text += " (" + ", ".join(sub_tags(s) for s in ac["from"]) + ")"
    d["ac"] = text

    d["hp"] = str(c["hp"]["average"]) + " (" + c["hp"]["formula"] + ")"
    
    if type(c["alignment"][0]) is str:
        d["alignment"] = "".join(c["alignment"])
    else:
        d["alignment"] = " or ".join("".join(a["alignment"]) + \
            " (" + str(a["chance"]) + "%)" for a in c["alignment"])

    traits = []
    for t in c.get("trait", []):
        trait = {"name": t["name"], "text": ""}
        for e in t["entries"]:
            try:
                text = e.replace("{@atk mw}", "melee weapon")
                if "{@atk" in text:
                    print(text)
                trait["text"] += sub_tags(text) + "\n\n"
            except:
                print(e)
    
    d["traits"] = traits

    out.append(d)

with open('out.json', 'w') as f:
    json.dump(out, f, indent=4)
