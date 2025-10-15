import json
import math
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

def strip_trailing_brackets(string: str, max: int = 1) -> str:
    i = 0
    while string.endswith("]") and i < max:
        string = string.removesuffix("]")
        i += 1
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

def str_is_valid_float(string: str) -> bool:
    try:
        float(string)
        return True
    except:
        return False

def round_off(string: str) -> str:
    if str_is_valid_float(string):
        return str(round(float(string)))
    else:
        return string

def parse_damage_body(rank: int, text: str) -> str:
    # Examples:
    #   @Damage[@item.level[persistent,acid]]
    #   @Damage[2d8[piercing],2d4[slashing]|options:area-damage]
    #   @Damage[(1d4+((@item.level)-1))[persistent,electricity]]
    #   @Damage[(@item.level)d4[persistent,mental]]
    #   @Damage[(2*ceil(@item.rank/2)-1)[bleed]] # TODO needs op precedence.
    # This function accepts the body of the tag.
    # If item.level or item.rank are present, they should be treated as 1.
    [text, *_] = text.split("|") # Discard tags.

    i = 0
    operand_stack = []
    operator_stack = []
    tok = ""
    ret = ""

    FUNCS = ["ceil", "floor", "ternary", "gte", "max"]
    OPS = ["+", "-", "*", "/"]

    def finish_tok():
        nonlocal tok
        if not tok:
            return
        elif tok in FUNCS:
            operator_stack.append(tok)
        elif tok == "@item.level" or tok == "@item.rank":
            operand_stack.append(str(rank))
        else:
            operand_stack.append(tok)
        tok = ""

    def precedence(op) -> int:
        if op in OPS:
            return OPS.index(op)
        else:
            return -1

    def process_op(op):
        rhs = operand_stack.pop()
        lhs = operand_stack.pop()
        if str_is_valid_float(lhs) and str_is_valid_float(rhs):
            rhs = float(rhs)
            lhs = float(lhs)
            if op == "+":
                result = lhs + rhs
            elif op == "-":
                result = lhs - rhs
            elif op == "*":
                result = lhs * rhs
            elif op == "/":
                result = lhs / rhs
            else:
                raise Exception(f"Unhandled operator '{op}' in: {text}")
            operand_stack.append(str(result))
        elif lhs == "0" or lhs == "0.0":
            operand_stack.append(rhs)
        elif rhs == "0" or rhs == "0.0":
            operand_stack.append(lhs)
        else:
            lhs = round_off(lhs)
            rhs = round_off(rhs)
            operand_stack.append(f"{lhs} {op} {rhs}")

    while i < len(text):
        c = text[i]
        if c == "[":
            finish_tok()
            j = i + 1
            while text[j] != "]":
                j += 1

            # Concatenate all values inside current brackets. To handle e.g.
            # (@spell.level - 1)d4[type] as 1d4 type.
            roll = round_off(operand_stack.pop())
            while operand_stack and operand_stack[-1] != "(":
                roll = round_off(operand_stack.pop()) + roll

            types = text[i + 1:j].replace(",", " ")
            if types == "bleed":
                # for some reason persistent is implicit in forge bleeds.
                types = "persistent bleed" 
            if types == "healing":
                types = ""
            if ret:
                ret += " and "
            ret += roll + " " + types
            i = j + 1
        elif c.isalnum() or c in ['@', '.']:
            tok += c
        elif c in OPS:
            finish_tok()
            while operator_stack and \
                precedence(operator_stack[-1]) > precedence(c):
                process_op(operator_stack.pop())
            operator_stack.append(c)
        elif c == "(":
            finish_tok()
            operator_stack.append("(")
        elif c == ")":
            finish_tok()
            op = operator_stack.pop()
            while op != "(":
                process_op(op)
                op = operator_stack.pop()
            if operator_stack and operator_stack[-1] in FUNCS:
                func = operator_stack.pop()
                if func == "ceil":
                    val = float(operand_stack.pop())
                    operand_stack.append(str(math.ceil(val)))
                if func == "floor":
                    val = float(operand_stack.pop())
                    operand_stack.append(str(math.floor(val)))
                elif func == "ternary":
                    if_false = operand_stack.pop()
                    if_true = operand_stack.pop()
                    boolval = operand_stack.pop()

                    if boolval == "True":
                        operand_stack.append(if_true)
                    else:
                        operand_stack.append(if_false)
                elif func == "gte":
                    rhs = operand_stack.pop()
                    lhs = operand_stack.pop()
                    operand_stack.append(str(float(lhs) >= float(rhs)))
                elif func == "max":
                    rhs = operand_stack.pop()
                    lhs = operand_stack.pop()
                    if float(rhs) > float(lhs):
                        operand_stack.append(rhs)
                    else:
                        operand_stack.append(lhs)
        elif c in [" ", ","]:
            finish_tok()
        else:
            raise Exception("Need to parse damage text: " + text)
        i += 1

    return ret

def normalise_tag_to_text(rank: int, tag: str) -> str:
    [tagname, body] = tag.split("[", 1)
    body = strip_trailing_brackets(body, 1)
    if tagname == "UUID":
        # Last segment of UUID is usually a nice human readable name.
        # E.g. UUID[Compendium.pf2e.conditionitems.Item.Grabbed]
        return body.rsplit(".", 1)[1]
    elif tagname == "Damage":
        try:
            return parse_damage_body(rank, body) 
        except Exception as e:
            print("Failed to parse damage: " + body)
            raise e
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
                "acrobatics", "arcana", "athletics", "crafting", "deception",
                "diplomacy", "intimidation", "medicine", "nature", "occultism",
                "perception", "performance", "religion", "society", "stealth",
                "survival", "thievery"
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
    else:
        raise Exception("unknown tag: " + tag)

def parse_description(rank: int, desc: str) -> str:
    ret = ""
    tag = None 
    tag_body = None
    tag_just_ended = None
    for c in desc:
        if tag is not None:
            tag += c
            if c == "]": 
                if tag.count("[") == tag.count("]"):
                    text = normalise_tag_to_text(rank, tag)
                    tag_just_ended = tag
                    tag = None
                    ret += text
        elif c == "@":
            tag = ""
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
    rank = sys["level"]["value"]

    print(path)

    return {
        "name": data["name"],
        "rank": sys["level"]["value"],
        "rarity": sys["traits"]["rarity"],
        "target": sys["target"]["value"],
        "range": sys["range"]["value"],
        "time": sys["time"]["value"],
        "duration": sys["duration"]["value"],
        "sustained": sys["duration"]["sustained"],
        "description": parse_description(rank, sys["description"]["value"]),
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
        print()

with open("pf2e_spells.json", "w") as f:
    json.dump(spells, f, indent=4)

