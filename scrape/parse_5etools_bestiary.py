import json
import re

ZERO_WIDTH_SPACE = "\u200b"

with open('temp.json', 'r') as f:
    creatures = json.load(f)

def sub_tags(string):
    string = string \
        .replace("{@atk mw}", "Melee weapon attack") \
        .replace("{@atk rw}", "Ranged weapon attack") \
        .replace("{@atk mw,rw}", "Melee or ranged weapon attack") \
        .replace("{@h}", "On hit: ") \
        .replace("{@recharge}", "(recharge on 6)")
    # {@hit n} -> +n
    string = re.sub(
        r'{@hit (\d+)}',
        r'+\1',
        string,
        flags=re.MULTILINE
    )
    # {@dc n} -> DC n
    string = re.sub(
        r'{@dc (\d+)}',
        r'DC \1',
        string,
        flags=re.MULTILINE
    )
    # {@recharge n} -> (recharge n-6)
    string = re.sub(
        r'{@recharge (\d+)}',
        r'(recharge \1-6)',
        string,
        flags=re.MULTILINE
    )
    # {@creature 5e.tools name||in text name} -> in text name
    string = re.sub(
        r'{@creature [\w ]*\|[\w ]*\|(\w+)}',
        r'\1',
        string,
        flags=re.MULTILINE
    )
    # {@chance n|n percent|hover text} -> n%
    string = re.sub(
        r'{@chance (\d+)\|[^\|]*\|[^\|]*}',
        r'\1%',
        string,
        flags=re.MULTILINE
    )
    # {@x y} -> y
    string = re.sub(
        r'{@\w+ ([\w\s\+\-\u00d7\. ]+)(\|phb)?}',
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
                for i in e["items"]:
                    if "entry" in i:
                        text += f"\u2022 {sub_tags(i['name'])}" \
                            f" {sub_tags(i['entry'])}\n"
                    else:
                        entry = sub_tags('\n\t'.join(i["entries"]))
                        text += f"\u2022 {sub_tags(i['name'])} {entry}\n"
        trait["text"] = text[:-2]
        traits.append(trait)
    return traits

def parse_legendary_actions(c):
    LEGENDARY_HEADER = \
        "The {@} can take 3 legendary actions, choosing from the options " \
        "below. Only one legendary action can be used at a time and only at " \
        "the end of another creature's turn. The {@} regains spent legendary " \
        "actions at the start of its turn."
    
    legendary = parse_traits(c.get("legendary", []))
    if legendary:
        if "legendaryHeader" in c:
            legendary.insert(
                0,
                {"name": ZERO_WIDTH_SPACE, "text": "\n".join(c["legendaryHeader"])}
            )
        else:
            legendary.insert(
                0,
                {
                    "name": ZERO_WIDTH_SPACE,
                    "text": LEGENDARY_HEADER.replace("{@}", c["name"])
                }
            )
        return legendary
    return None

def parse_speed(speed):
    entries = []
    for s in speed:
        if type(speed[s]) is int:
            entries.append(f'{s} {speed[s]} ft.')
            continue
        if type(speed[s]) is bool:
            continue
        entries.append(f"{s} {speed[s]['number']} ft. {speed[s]['condition']}")
    return ", ".join(entries)

out = []
for c in creatures:
    d = {k: c.get(k) for k in
        [
            "name",
            "size",
            "type",
            "str",
            "dex",
            "con",
            "int",
            "wis",
            "cha",
            "languages",
            "cr",
            "speed",
            "save",
            "skill",
            "senses"
        ]
    }

    d["ac"] = get_ac(c)
    d["hp"] = str(c["hp"]["average"]) + " (" + c["hp"]["formula"] + ")"
    d["alignment"] = get_aligment(c)
    d["speed"] = parse_speed(c.get("speed", {}))
    d["traits"] = parse_traits(c.get("trait", []))    
    d["actions"] = parse_traits(c.get("action", []))
    d["legendary_actions"] = parse_legendary_actions(c)

    out.append(d)

with open('out.json', 'w') as f:
    json.dump(out, f, indent=4)
