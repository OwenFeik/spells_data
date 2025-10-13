import json
import os.path
import pathlib
import subprocess
import tempfile
import traceback
import sys

def clone_repository() -> pathlib.Path: 
    directory = tempfile.mkdtemp()
    repository = "https://github.com/foundryvtt/pf2e.git"
    subprocess.check_call(["git", "clone", repository, str(directory)])
    return pathlib.Path(directory)

def spell_files(repo: pathlib.Path) -> list[pathlib.Path]:
    files = []
    spells_dir = repo.joinpath("packs/spells")
    for entry in os.listdir(spells_dir):
        dir = spells_dir.joinpath(entry)
        if os.path.isdir(dir):
            for entry in os.listdir(dir):
                file = dir.joinpath(entry)
                if os.path.isfile(file):
                    files.append(file)
    return files

def strip_trailing_brackets(string: str) -> str:
    while string.endswith("]"):
        string = string.removesuffix("]")
    return string

def parse_tag_body(tag_body: str) -> dict[str, str]:
    entries = {}
    for entry in tag_body.split("|"):
        [key, *rest] = entry.split(":", 1)
        if len(rest) == 0:
            value = ""
        else:
            value = rest[0]
        entries[key] = value
    return entries

def parse_damage_body(text: str) -> str:


def normalise_tag_to_text(tag: str) -> str:
    [tagname, body] = tag.split("[", 1)
    body = strip_trailing_brackets(body)
    if tagname == "UUID":
        # Last segment of UUID is usually a nice human readable name.
        # E.g. UUID[Compendium.pf2e.conditionitems.Item.Grabbed]
        return body.rsplit(".", 1)[1]
    elif tagname == "Damage":
        # E.g. Damage[10d6[bludgeoning]]
        [roll, rest] = body.split("[", 1)
        if "|" in rest:
            [rest, _] = rest.split("|", 1) # Discard traits, etc.
        damage = strip_trailing_brackets(rest).replace(",", " ")
        if not damage.replace(" ", "x").isalnum():
            raise Exception("weird damage text: " + damage + " (" + tag + ")")
        return roll + " " + damage
    elif tagname == "Check":
        # E.g. Check[flat|dc:3], Check[fortitude|against:spell]
        params = parse_tag_body(body)
        if "flat" in params:
            ty = "flat check"
        elif "fortitude" in params:
            ty = "Fortitude save"
        elif "reflex" in params:
            ty = "Reflex save"
        elif "will" in params:
            ty = "Will save"
        else:
            SKILLS = [
                "acrobatics", "arcana", "athletics", "medicine", "perception",
                "stealth", "thievery"
            ]
            for skill in SKILLS:
                if skill in params:
                    ty = skill.capitalize() + " check"
                    break
            else:
                raise Exception("unknown check kind: " + tag)
        if "dc" in params:
            return f"DC {params['dc']} {ty}"
        else:
            return ty
    elif tagname == "Template":
        params = parse_tag_body(body) 
        for template_ty in ["emanation", "burst", "line", "cone"]:
            if template_ty in params:
                ty = template_ty
                break
        else:
            if "type" in params:
                ty = params["type"]
            else:
                raise Exception("unknown template type in template: " + tag) 
        distance = params["distance"]
        return f"{distance}-foot {ty}" 
    elif "item.level" in tagname or "item.rank" in tagname:
        # Appears in nested tags like @Damage[@item.level[persistent,acid]].
        # Convert this to 1[persistent,acid] to then be expanded as damage.
        # TODO parse arithmetic roll expressions.
        # E.g. @Damage[2d8[piercing],2d4[slashing]|options:area-damage]
        tag = tag.replace("item.level", "1").replace("item.rank", "1")
        if ")" in tag:
            end_of_expr = tag.rindex(")")
            expr = tag[:end_of_expr + 1]
            while expr.count(")") > expr.count("("):
                end_of_expr -= 1
                expr = tag[:end_of_expr + 1]
            rest = tag[end_of_expr + 1:]
        elif "[" in tag:
            end_of_expr = tag.index("[")
            expr = tag[:end_of_expr]
            rest = tag[end_of_expr:]
        else:
            print("body =", tag)
            raise Exception("failed to parse item.level expr: " + tag)
        try:
            value = eval(expr)
        except:
            print("tag  =", tag)
            print("expr =", expr)
            print("rest =", rest)
            raise Exception("failed to parse item.level expr: " + tag)
        if value == 0:
            value = ""
        else:
            value = str(value)
        return f"{value}{rest}"
    else:
        raise Exception("unknown tag: " + tag)

def parse_description(desc: str) -> str:
    ret = ""
    tag_stack = []
    tag_body = None
    tag_just_ended = None
    for c in desc:
        if c == "@":
            # Sometimes a tag is in an expression like "@Damage[(@item.rank..."
            tag = ""
            while len(tag_stack) > 0 and tag_stack[-1].endswith("("):
                tag += "("
                tag_stack[-1] = tag_stack[-1][:-1]
            tag_just_ended = None
            tag_stack.append(tag)
        elif tag_stack:
            tag_just_ended = None
            tag_stack[-1] += c
            if c == "]": 
                current_tag = tag_stack[len(tag_stack) - 1]
                if current_tag.count("[") == current_tag.count("]"):
                    text = normalise_tag_to_text(current_tag)
                    tag_stack.pop()
                    if tag_stack:
                        tag_stack[-1] += text
                    else:
                        ret += text
                        tag_just_ended = text
        elif c == "{" and tag_just_ended:
            tag_body = ""
        elif c == "}" and tag_body and tag_just_ended:
            ret = ret.removesuffix(tag_just_ended) + tag_body
            tag_body = None
            tag_just_ended = None
        elif tag_body is not None:
            tag_body += c
        else:
            tag_just_ended = None
            ret += c

    return ret

def parse_spell_file(path: pathlib.Path) -> dict:
    with open(path, "r") as f:
        data = json.load(f)
    sys = data["system"]

    return {
        "name": data["name"],
        "rank": sys["level"]["value"],
        "rarity": sys["traits"]["rarity"],
        "target": sys["target"]["value"],
        "range": sys["range"]["value"],
        "time": sys["time"]["value"],
        "duration": sys["duration"]["value"],
        "sustained": sys["duration"]["sustained"],
        "description": parse_description(sys["description"]["value"]),
        "traditions": sys["traits"]["traditions"],
        "traits": sys["traits"]["value"],
        "publication": sys["publication"]["title"],
    }



if len(sys.argv) < 2:
    repo_path = clone_repository()
else:
    repo_path = pathlib.Path(sys.argv[1])

spells = []
for spell_file in spell_files(repo_path):
    try:
        spells.append(parse_spell_file(spell_file))
    except Exception as e:
        traceback.print_exception(e)
        print("Occurred when parsing " + str(spell_file))

with open("pf2e_spells.json", "w") as f:
    json.dump(spells, f, indent=4)

