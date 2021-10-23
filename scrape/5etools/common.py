import re

def sub_tags(string):
    string = string \
        .replace("\u2014", " - ") \
        .replace("\u2013", " - ") \
        .replace("\u2212", "-") \
        .replace("\u00d7", "x") \
        .replace("{@atk mw}", "Melee weapon attack") \
        .replace("{@atk rw}", "Ranged weapon attack") \
        .replace("{@atk mw,rw}", "Melee or ranged weapon attack") \
        .replace("{@atk ms,rs}", "Melee or ranged spell attack") \
        .replace("{@h}", "On hit: ") \
        .replace("{@recharge}", "(recharge on 6)") \
        .replace("{@hitYourSpellAttack}", "your spell attack modifier") \
        .replace(
            "rs {@hitYourSpellAttack}",
            "Ranged spell attack: your spell attack modifier"
        ) \
        .replace(
            "ms {@hitYourSpellAttack}",
            "Melee spell attack: your spell attack modifier"
        )
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
        r'{@creature ([\w\(\)\, ]*)\|[^{}]+}',
        r"\1",
        string,
        flags=re.MULTILINE
    )
    # {@creature 5e.tools name||in text name} -> in text name
    string = re.sub(
        r'{@creature [\w\(\)\, ]*\|[\w\(\)\, ]*\|([\w\,\(\) ]+)}',
        r"\1",
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
        r"\1",
        string,
        flags=re.MULTILINE
    )
    # {@item name|set|text} -> text
    string = re.sub(
        r"{@item [\w'\+\-\(\)\, ]+\|[\w'\+\-\(\)\, ]*\|([\w'\+\-\(\)\, ]*)}",
        r"\1",
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
        r"\1",
        string,
        flags=re.MULTILINE
    )
    # {@spell link name||in text name} -> in text name
    string = re.sub(
        r'{@spell [^\{\}\|]+\|[^\{\}\|]*(\|[^\{\}\|]*)?}',
        r"\1",
        string,
        flags=re.MULTILINE
    )
    # {@book in text name|book|chapter|title} -> in text name
    string = re.sub(
        r"{@book ([\w'\+\-\(\) ]+)\|[\w'\+\-\(\) ]*\|"
        r"[\w'\+\-\(\)\= ]*\|[\w'\+\-\(\)\= ]*}",
        r"\1",
        string,
        flags=re.MULTILINE
    )
    # {@condition name||other text} -> name
    string = re.sub(
        r"{@(condition|filter|adventure|classFeature) ([\w/ ]+)\|[^{}]*}",
        r"\2",
        string,
        flags=re.MULTILINE
    )
    # {@dice roll|average} -> average
    string = re.sub(
        r"{@dice ([0-9d\-+ ]+)\|(\d+)}",
        r"\1 (\2)",
        string,
        flags=re.MULTILINE
    )
    # {@chance chance|in text} -> in text
    string = re.sub(
        r"{@chance \d+\|([^{}]*)}",
        r"\1",
        string,
        flags=re.MULTILINE
    )
    # {@race internal name||Visible name}
    string = re.sub(
        r"{@race [^{}\|]+\|\|([^{}\|]+)}",
        r"\1",
        string,
        flags=re.MULTILINE
    )
    # {@x y} -> y
    string = re.sub(
        r"{@\w+ ([^\{\}\|]+)(\|(phb|GoS|DMG))?}",
        r"\1",
        string,
        flags=re.MULTILINE
    )
    # {x y} -> y
    string = re.sub(
        r"{@\w+ ([^{}\|]+)(\|[^{}]*)?}",
        r"\1",
        string,
        flags=re.MULTILINE
    )
    return string
