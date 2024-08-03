import json

import xmltodict
import os

from pathlib import Path

titles = {}
def walk_directory_with_pathlib(directory):
    path = Path(directory)
    for entry in path.iterdir():
        if entry.is_dir():
            walk_directory_with_pathlib(entry)  # 递归调用
        else:
            if entry.name == "Title.xml":
                with open(entry, 'r', encoding='utf-8') as f:
                    data = xmltodict.parse(f.read())
                    titles[str(data["TitleData"]["name"]["id"])] = {
                        "title": str(data["TitleData"]["name"]["str"]),
                        "rareType": str(data["TitleData"]["rareType"])
                    }


# 使用示例
walk_directory_with_pathlib(r'G:\SDGB_1.40.00_20240222213447_0\Package\Sinmai_Data\StreamingAssets\A000\title')

with open("title_list.json", "w", encoding="utf-8") as f:
    json.dump(titles, f, ensure_ascii=False, indent=4)
