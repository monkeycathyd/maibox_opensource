import datetime
import json

import requests

raw_alias = requests.get("https://maimai.lxns.net/api/v0/maimai/alias/list").json()["aliases"]

new_alias = {}
date = datetime.datetime.now()

for alias in raw_alias:
    for alia in alias["aliases"]:
        if alia not in new_alias.keys():
            new_alias[alia] = []
        new_alias[alia].append(alias["song_id"])

with open("../game_data/song_alias_list.json", "w", encoding="utf-8") as f:
    f.write(json.dumps({
        "info": {
            "version": f"lxns_alias-{date.strftime('%Y%m%d')}",
            "date": date.strftime("%Y-%m-%d %H:%M:%S")
        },
        "data": new_alias
    }, indent=2, ensure_ascii=False))