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

def normalise_tag_to_text(tag: str) -> str:
    [tagname, body] = tag.split("[", 1)
    if tagname == "UUID":
        # Last segment of UUID is usually a nice human readable name.
        # E.g. UUID[Compendium.pf2e.conditionitems.Item.Grabbed]
        return strip_trailing_brackets(body.rsplit(".", 1)[1])
    if tagname == "Damage":
        # E.g. Damage[10d6[bludgeoning]]
        [roll, rest] = body.split("[", 1)
        if "|" in rest:
            [rest, _] = rest.split("|", 1) # Discard traits, etc.
        damage = strip_trailing_brackets(rest).replace(",", " ")
        if not damage.replace(" ", "x").isalnum():
            raise Exception("weird damage text: " + damage + " (" + tag + ")")
        return roll + " " + damage
    if tagname == "Check":
        # E.g. Check[flat|dc:3], Check[fortitude|against:spell]
        [kind, rest] = body.split("|", 1)
        if kind == "flat":
            [_dc, dc] = rest.removesuffix("]").split(":", 1)
            assert _dc == "dc"
            return f"DC {dc} flat check"
        else:
            raise Exception("unknown check kind: " + tag)
    if tagname == "Template":
        params = strip_trailing_brackets(body).split("|")
        assert len(params) > 0
        assert params[0].startswith("type:")
        ty = params[0].removeprefix("type:")
        if ty == "emanation":
            assert params[1].startswith("distance:")
            distance = params[1].removeprefix("distance:")
            return distance + "-foot emanation"
        else:
            raise Exception("unknown template type: " + ty + " (" + tag + ")")
    else:
        raise Exception("unknown tag: " + tag)
    return body


def parse_description(desc: str) -> str:
    ret = ""
    tag_stack = []
    tag_body = ""
    tag_just_ended = None
    for c in desc:
        if c == "@":
            tag_just_ended = None
            tag_stack.append("")
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
        elif c == "}" and tag_just_ended:
            ret = ret.removesuffix(tag_just_ended) + tag_body
            tag_body = ""
            tag_just_ended = None
        elif tag_just_ended:
            tag_body += c
        else:
            tag_just_ended = None
            ret += c

    return ret

def parse_spell_file(path: pathlib.Path) -> dict:
    with open(path, "r") as f:
        data = json.load(f)
    sys = data["system"]

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

