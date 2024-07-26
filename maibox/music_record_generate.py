import json
import os
from datetime import datetime

from jinja2 import FileSystemLoader, Environment, ModuleLoader

from maibox import config
from maibox.HTTPRequest import HTTPRequest

cfg = config.get_config()

template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "templates"))
music_info_path = os.path.join(os.path.dirname(__file__), "game_data", "music_list.json")

with open(music_info_path, "r", encoding="utf-8") as f:
    music_list = json.load(f)

comboStatus_list = ["back", "fc", "fcp", "ap", "app"]
syncStatus_list = ["back", "fs", "fsp", "fdx", "fdxp", "sync"]
level_list = ['0', '1', '2', '3', '4', '5', '6', '7', '7+', '8',
              '8+', '9', '9+', '10', '10+', '11', '11+', '12',
              "12+", '13', "13+", '14', "14+", '15', "15+"]
difficulty_list = ["basic", "advanced", "expert", "master", "remaster", "utage"]

def standard_achievement(num: int):
    return str(int(f'{num:07d}'[:3])) + "." + f'{num:07d}'[3:] + "%"

def get_rating(achievement_rate):
    if 100.5 <= achievement_rate <= 101.0:
        return "SSSp"
    elif 100.0 <= achievement_rate < 100.5:
        return "SSS"
    elif 99.5 <= achievement_rate < 100.0:
        return "SSp"
    elif 99.0 <= achievement_rate < 99.5:
        return "SS"
    elif 98.0 <= achievement_rate < 99.0:
        return "Sp"
    elif 97.0 <= achievement_rate < 98.0:
        return "S"
    elif 94.0 <= achievement_rate < 97.0:
        return "AAA"
    elif 90.0 <= achievement_rate < 94.0:
        return "AA"
    elif 80.0 <= achievement_rate < 90.0:
        return "A"
    elif 75.0 <= achievement_rate < 80.0:
        return "BBB"
    elif 70.0 <= achievement_rate < 75.0:
        return "BB"
    elif 60.0 <= achievement_rate < 70.0:
        return "B"
    elif 50.0 <= achievement_rate < 60.0:
        return "C"
    else:
        return "D"

def get_level(music_id, level):
    level = music_list[str(music_id)]["chart_difficulty"][int(level)]
    if round(level) != level:
        return str(int(level)) + "+"
    return str(int(level))

def get_user_music_details(uid: int):
    """
    获取并处理指定用户ID的音乐详情。

    :param uid: 用户ID
    :return: 用户音乐详情列表
    """
    req = HTTPRequest(uid)
    data = req.Request("GetUserMusicApiMaimaiChn", {"userId": uid, "nextIndex": 0, "maxCount": 2147483647})
    userMusicDetailList = [detail for music in data["userMusicList"] for detail in music["userMusicDetailList"]]

    final_list = []
    for music in userMusicDetailList:
        try:
            final_list.append({
                "title": music_list[str(music["musicId"])]["title"],
                "achievement": standard_achievement(int(music["achievement"])),
                "comboStatus": comboStatus_list[music["comboStatus"]],
                "syncStatus": syncStatus_list[music["syncStatus"]],
                "musicId": music["musicId"],
                "difficulty": difficulty_list[music["level"] if music["level"] < 6 else -1],
                "deluxscoreMax": music["deluxscoreMax"],
                "rate": get_rating(float(standard_achievement(int(music["achievement"]))[:-1])).lower(),
                "level": get_level(music["musicId"], level_list[music["level"]]),
                "chart_type": "dx" if len(str(music["musicId"])) >= 5 and str(music["musicId"])[0] == "1" else "standard"
            })
        except:
            continue

    return final_list

def render_html(uid: int):
    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template("music_records.html")
    return template.render(
        music_list=get_user_music_details(uid),
        mai_version=cfg["mai_encoding"],
        gen_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )