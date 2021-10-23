import json

import requests

import parse_bestiary

ROOT_URL = "https://5e.tools/data/bestiary/"
VERSION = "?v=1.122.8"
INDEX_URL = ROOT_URL + "index.json" + VERSION

out = []
for f in requests.get(INDEX_URL).json().values():
    try:
        data = requests.get(ROOT_URL + f + VERSION).json()["monster"]
    except:
        print(f)

    out.extend(parse_bestiary.parse_json(data))

with open("out.json", "w") as f:
    json.dump(out, f, indent=4)
