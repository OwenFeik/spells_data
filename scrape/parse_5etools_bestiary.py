import json
import re

ZERO_WIDTH_SPACE = "\u200b"

def sub_tags(string):
    string = string \
        .replace("{@atk mw}", "Melee weapon attack") \
        .replace("{@atk rw}", "Ranged weapon attack") \
        .replace("{@atk mw,rw}", "Melee or ranged weapon attack") \
        .replace("{@atk ms,rs}", "Melee or ranged spell attack") \
        .replace("{@h}", "On hit: ") \
        .replace("{@recharge}", "(recharge on 6)") \
        .replace("rs {@hitYourSpellAttack}", "Ranged spell attack: your spell attack modifier") \
        .replace("ms {@hitYourSpellAttack}", "Melee spell attack: your spell attack modifier") \
        .replace("{@hitYourSpellAttack}", "your spell attack modifier")
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
    # {@creature in text name|set} -> in text name
    string = re.sub(
        r'{@creature ([\w\(\)\, ]*)\|\w+}',
        r'\1',
        string,
        flags=re.MULTILINE
    )
    # {@creature 5e.tools name||in text name} -> in text name
    string = re.sub(
        r'{@creature [\w\(\)\, ]*\|[\w\(\)\, ]*\|([\w\,\(\) ]+)}',
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
    # {@item name|set} -> name
    string = re.sub(
        r"{@item ([\w'\+\-\(\) ]+)\|[\w'\+\-\(\) ]*}",
        r'\1',
        string,
        flags=re.MULTILINE
    )
    # {@item name|set|text} -> text
    string = re.sub(
        r"{@item [\w'\+\-\(\)\, ]+\|[\w'\+\-\(\)\, ]*\|([\w'\+\-\(\)\, ]*)}",
        r'\1',
        string,
        flags=re.MULTILINE
    )
    # {@table name|set} -> name table
    string = re.sub(
        r'{@table ([^\{\}\|]+)(\|(phb|GoS|DMG))?}',
        r'\1 table',
        string,
        flags=re.MULTILINE
    )
    # {@filter in text name|location|type=name} -> in text name
    string = re.sub(
        r"{@filter ([\w'\+\-\(\) ]+)\|[\w'\+\-\(\) ]*\|[\w'\+\-\(\)\= ]*}",
        r'\1',
        string,
        flags=re.MULTILINE
    )
    # {@spell link name||in text name} -> in text name
    string = re.sub(
        r'{@spell [^\{\}\|]+\|[^\{\}\|]*(\|[^\{\}\|]*)?}',
        r'\1',
        string,
        flags=re.MULTILINE
    )
    # {@book in text name|book|chapter|title} -> in text name
    string = re.sub(
        r"{@book ([\w'\+\-\(\) ]+)\|[\w'\+\-\(\) ]*\|[\w'\+\-\(\)\= ]*\|[\w'\+\-\(\)\= ]*}",
        r'\1',
        string,
        flags=re.MULTILINE
    )
    # {@x y} -> y
    string = re.sub(
        r'{@\w+ ([^\{\}\|]+)(\|(phb|GoS|DMG))?}',
        r'\1',
        string,
        flags=re.MULTILINE
    )
    return string

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
