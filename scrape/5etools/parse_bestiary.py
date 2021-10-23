from common import sub_tags

ZERO_WIDTH_SPACE = "\u200b"

def get_size(c):
    return {
        "T": "Tiny",
        "S": "Small",
        "M": "Medium",
        "L": "Large",
        "H": "Huge",
        "G": "Gargantuan"
    }[c["size"]]

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

def get_hp(hp):
    if "average" in hp and "formula" in hp:
        return str(hp["average"]) + " (" + hp["formula"] + ")"
    else:
        return hp["special"]

def get_alignment(c):
    if not "alignment" in c:
        return ""
    if type(c["alignment"][0]) is str:
        return "".join(c["alignment"])
    else:
        entries = []
        for a in c["alignment"]:
            if "chance" in a:
                entries.append(
                    "".join(a["alignment"]) + "(" + str(a["chance"]) + "%)"
                )
            elif "special" in a:
                entries.append(a["special"])
            else:
                entries.append("".join(a["alignment"]))

        return " or ".join(entries)

def parse_traits(l):
    traits = []
    for t in l:
        trait = {"name": sub_tags(t["name"]) if "name" in t else ZERO_WIDTH_SPACE}
        text = ""
        for e in t["entries"]:
            if type(e) is str: # single line of text
                text += sub_tags(e) + "\n\n"
            elif "entries" in e and "type" in e and e["type"] == "inline":
                for i in e["entries"]:
                    if type(i) is str:
                        text += sub_tags(i)
                    else:
                        text += sub_tags(i["text"])
            else: # list of items
                for i in e["items"]:
                    if type(i) is str:
                        text += f"\u2022 {sub_tags(i)}\n"
                    elif "entry" in i:
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
    try:
        for s in speed:
            if type(speed[s]) is int:
                entries.append(f'{s} {speed[s]} ft.')
            elif type(speed[s]) is bool:
                continue
            elif s == "choose":
                entries.append(f"choose from {', '.join(speed[s]['from'])} " \
                    f"{speed[s]['amount']} ft. {speed[s]['note']}")
            else:
                entries.append(f"{s} {speed[s]['number']} ft. {speed[s]['condition']}")
    except:
        print(speed)
    return ", ".join(entries)

def parse_json(creatures):
    out = []
    for c in creatures:
        if "_copy" in c:
            continue

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

        d["saves"] = d["save"]
        del d["save"]
        d["skills"] = d["skill"]
        del d["skill"]

        d["size"] = get_size(c)
        d["ac"] = get_ac(c)
        d["hp"] = get_hp(c["hp"])
        d["alignment"] = get_alignment(c)
        d["speed"] = parse_speed(c.get("speed", {}))
        d["traits"] = parse_traits(c.get("trait", []))    
        d["actions"] = parse_traits(c.get("action", []))
        d["legendary_actions"] = parse_legendary_actions(c)

        out.append(d)
    return out
