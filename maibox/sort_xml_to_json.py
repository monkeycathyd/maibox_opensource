import json
import xmltodict

with open("game_data/IconSort.xml", "r", encoding="utf-8") as f:
    data = xmltodict.parse(f.read())

new_data = {}
for item in data["SerializeSortData"]["SortList"]["StringID"]:
    new_data[item["id"]] = item["str"]

with open("game_data/icon_list.json", "w", encoding="utf-8") as f:
    json.dump(new_data, f, ensure_ascii=False, indent=4)