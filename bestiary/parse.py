import json
import re

with open('temp.json', 'r') as f:
    creatures = json.load(f)

def sub_tags(string):
    string = string \
        .replace("{@atk mw}", "melee weapon attack") \
        .replace("{@atk rw}", "ranged weapon attack") \
        .replace("{@atk mw, rw}", "melee or ranged weapon attack") \
        .replace("{@h}", "On hit: ") \
        .replace("{@recharge}", "(recharge on 6)")
    string = re.sub(
        r'{@hit (\d+)}',
        r'+\1',
        string,
        flags=re.MULTILINE
    )
    string = re.sub(
        r'{@dc (\d+)}',
        r'DC \1',
        string,
        flags=re.MULTILINE
    )
    string = re.sub(
        r'{@recharge (\d+)}',
        r'(recharge \1-6)',
        string,
        flags=re.MULTILINE
    )
    string = re.sub(
        r'{@\w+ ([\w\s\+\- ]+)(\|phb)?}',
        r'\1',
        string,
        flags=re.MULTILINE
    )
    return string

def get_ac(c):
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
    return text

def get_aligment(c):
    if type(c["alignment"][0]) is str:
        return "".join(c["alignment"])
    else:
        return " or ".join("".join(a["alignment"]) + \
            " (" + str(a["chance"]) + "%)" for a in c["alignment"])

def parse_traits(l):
    traits = []
    for t in l:
        trait = {"name": sub_tags(t["name"])}
        text = ""
        for e in t["entries"]:
            if type(e) is str: # single line of text
                text += sub_tags(e) + "\n\n"
            else: # list of items
                try:
                    for i in e["items"]:
                        if "entry" in i:
                            text += f"\u2022 {sub_tags(i['name'])} {sub_tags(i['entry'])}\n"
                        else:
                            entry = sub_tags('\n\t'.join(i["entries"]))
                            text += f"\u2022 {sub_tags(i['name'])} {entry}\n"
                except:
                    print(e)
        trait["text"] = text[:-2]
        traits.append(trait)
    return traits

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

    d["ac"] = get_ac(c)
    d["hp"] = str(c["hp"]["average"]) + " (" + c["hp"]["formula"] + ")"
    d["alignment"] = get_aligment(c)
    d["traits"] = parse_traits(c.get("trait", []))    
    d["actions"] = parse_traits(c.get("action", []))

    out.append(d)

with open('out.json', 'w') as f:
    json.dump(out, f, indent=4)
