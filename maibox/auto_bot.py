import random

import time
from datetime import datetime, timedelta

import requests

from maibox.HTTPRequest import HTTPRequest

from maibox.config import get_config, get_config_with_reload

config = get_config()


ticket_define = {
    2:{"id": 2,"cost": 1},
    3:{"id": 3,"cost": 2},
    4:{"id": 4,"cost": 3},
    5:{"id": 5,"cost": 4},
    6:{"id": 6,"cost": 5}
}

region_map = [
    "北京市",
    "重庆市",
    "上海市",
    "天津市",
    "安徽省",
    "福建省",
    "甘肃省",
    "广东省",
    "贵州省",
    "海南省",
    "河北省",
    "黑龙江省",
    "河南省",
    "湖北省",
    "湖南省",
    "江苏省",
    "江西省",
    "吉林省",
    "辽宁省",
    "青海省",
    "陕西省",
    "山东省",
    "山西省",
    "四川省",
    "台湾省",
    "云南省",
    "浙江省",
    "广西壮族自治区",
    "内蒙古自治区",
    "宁夏回族自治区",
    "新疆维吾尔自治区",
    "西藏自治区"
]

def get_preview(uid, dao):
    result = {"is_success": False, "is_error": False, "user_id": uid, "data":{}, "msg": "", "is_in_whitelist": False}
    if config["whitelist_enabled"] and dao:
        if dao.isWhitelist(uid):
            result["is_in_whitelist"] = True
    else:
        result["is_in_whitelist"] = True
    login_dict = {
        "userId": uid,
        "accessCode": "",
        "regionId": config["region_id"],
        "placeId": config["place_id"],
        "clientId": config["key_chip"],
        "dateTime": int(time.time()),
        "isContinue": False,
        "genericFlag": 0
    }
    request = HTTPRequest(uid=uid)
    preview = request.Request("GetUserPreviewApiMaimaiChn", login_dict)
    result["data"] = preview
    result["is_success"] = True
    result["is_error"] = False
    result["msg"] = "成功"
    return result


def send_ticket(uid, ticket_id):
    result = {"is_success": False, "is_got_qr_code": True, "is_already_login": False, "is_already_had_ticket": False, "is_error": False, "user_id": uid, "msg": ""}
    login_dict = {
        "userId": uid,
        "accessCode": "",
        "regionId": config["region_id"],
        "placeId": config["place_id"],
        "clientId": config["key_chip"],
        "dateTime": int(time.time()),
        "isContinue": False,
        "genericFlag": 0
    }

    request = HTTPRequest(uid=uid)
    preview = request.Request("GetUserPreviewApiMaimaiChn", login_dict)
    if not preview["isLogin"]:
        login = request.Request("UserLoginApiMaimaiChn", login_dict)
        if login["returnCode"] != 1:
            result["is_got_qr_code"] = False
            result["msg"] = "请在微信“舞萌 中二”服务号上点击一次“玩家二维码”按钮后再试一遍"
            return result
    else:
        result["is_already_login"] = True
    user_data = request.Request("GetUserDataApiMaimaiChn", login_dict)
    charges = request.Request("GetUserChargeApiMaimaiChn", login_dict)

    had_ticket = False
    if charges["userChargeList"]:
        for charge in charges["userChargeList"]:
            if charge["stock"] > 0 and charge["chargeId"] == int(ticket_id):
                had_ticket = True
                result["is_already_had_ticket"] = True
                result["msg"] = "无法重复发放跑图票"
                break

    if not had_ticket:
        date_time = datetime.now()
        timestamp_str = date_time.strftime('%Y-%m-%d %H:%M:%S.0')
        expire_timestamp = (date_time + timedelta(days=90)).strftime('%Y-%m-%d 04:00:00')
        ticket_dict = {
            "userId": uid,
            "userChargelog": {
                "chargeId": ticket_id,
                "price": ticket_define[ticket_id]["cost"],
                "purchaseDate": timestamp_str,
                "playCount": int(user_data["userData"]["playCount"]),
                "playerRating": int(user_data["userData"]["playerRating"]),
                "placeId": config["place_id"],
                "regionId": config["region_id"],
                "clientId": config["key_chip"],
            },
            "userCharge": {
                "chargeId": ticket_id,
                "stock": 1,
                "purchaseDate": timestamp_str,
                "validDate": expire_timestamp
            }
        }

        try:
            request.Request("UpsertUserChargelogApiMaimaiChn", ticket_dict)
            result["is_success"] = True
            result["msg"] = "成功"
        except Exception as e:
            print(e.with_traceback(None))
            result["is_error"] = True
            result["msg"] = f"未知错误：{e.with_traceback(None)}"

    if not preview["isLogin"]:
        request.Request("UserLogoutApiMaimaiChn", login_dict)

    return result


def logout(uid, timestamp=0):
    result = {"is_success": False, "is_error": False, "user_id": uid, "msg": ""}
    login_dict = {
        "userId": uid,
        "accessCode": "",
        "placeId": config["place_id"],
        "regionId": config["region_id"],
        "clientId": config["key_chip"],
        "dateTime": timestamp,
        "isContinue": False,
        "type":5
    }
    try:
        request = HTTPRequest(uid=uid)
        resp = request.Request("UserLogoutApiMaimaiChn", login_dict)
        result["is_success"] = True
        result["msg"] = "成功"
    except Exception as e:
        e.with_traceback(None)
        result["is_error"] = True
        result["msg"] = f"未知错误：{e.with_traceback(None)}"

    return result

def dump_user_all(uid):
    result = {"is_success": False, "is_got_qr_code": True, "is_error": False, "user_id": uid, "data": {}, "msg": ""}

    available_attrs = ["UserData", "UserExtend", "UserOption", "UserActivity", "UserCharacter", "UserItem",
                       "UserLoginBonus", "UserMap", "UserMusic"]
    data = {}

    login_time = int(time.time())

    login_dict = {
        "userId": uid,
        "accessCode": "",
        "regionId": config["region_id"],
        "placeId": config["place_id"],
        "clientId": config["key_chip"],
        "dateTime": login_time,
        "isContinue": False,
        "genericFlag": 0
    }

    request = HTTPRequest(uid=uid)
    preview = request.Request("GetUserPreviewApiMaimaiChn", login_dict)
    if not preview["isLogin"]:
        login = request.Request("UserLoginApiMaimaiChn", login_dict)
        if login["returnCode"] != 1:
            result["is_got_qr_code"] = False
            result["msg"] = "请在微信“舞萌 中二”服务号上点击一次“玩家二维码”按钮后再试一遍"
            return result
    else:
        result["is_already_login"] = True

    for ava_attr in available_attrs:
        for i in range(0, 1):
            try:
                api = f"Get{ava_attr}Api"
                final_attr = ava_attr[0].lower() + ava_attr[1:]

                query = {"userId": uid, "nextIndex": 10000000000 if final_attr == "userItem" else 0,
                         "maxCount": 2147483647}
                resp = request.Request(api, datas=query)
                if final_attr in resp:
                    match final_attr:
                        case "userActivity":
                            data["userActList"] = resp["userActivity"]["playList"] + resp["userActivity"]["musicList"]
                        case _:
                            data[final_attr] = resp[final_attr]
                else:
                    match final_attr:
                        case "userMusic":
                            data["userMusicDetailList"] = []
                            for music in resp["userMusicList"]:
                                data["userMusicDetailList"] += music["userMusicDetailList"]
                        case _:
                            data[final_attr + "List"] = resp[final_attr + "List"]
                break
            except Exception as e:
                continue
    data["userFavoriteList"] = []
    data["userFriendSeasonRankingList"] = []
    data["userGeneralDataList"] = []
    data["userPlaylogList"] = []
    data["userRateList"] = []
    data["userUdemae"] = {
        "rate": 0,
        "maxRate": 0,
        "classValue": 0,
        "maxClassValue": 0,
        "totalWinNum": 0,
        "totalLoseNum": 0,
        "maxWinNum": 0,
        "maxLoseNum": 0,
        "winNum": 0,
        "loseNum": 0,
        "npcTotalWinNum": 0,
        "npcTotalLoseNum": 0,
        "npcMaxWinNum": 0,
        "npcMaxLoseNum": 0,
        "npcWinNum": 0,
        "npcLoseNum": 0
    }

    if not preview["isLogin"]:
        request.Request("UserLogoutApiMaimaiChn", login_dict)
    result["is_success"] = True
    result["msg"] = "成功"
    result["data"] = data
    return result

def query_ticket(uid):
    result = {"is_success": False, "is_error": False, "user_id": uid, "data": {}, "msg": ""}
    request = HTTPRequest(uid=uid)
    ticket = request.Request("GetUserChargeApiMaimaiChn", {"userId": uid})
    if not ticket["userChargeList"]:
        ticket["userChargeList"] = []
    result["data"] = ticket
    result["is_success"] = True
    result["is_error"] = False
    result["msg"] = "成功"
    return result

def get_user_region(uid):
    result = {"is_success": False, "is_error": False, "user_id": uid, "data": {}, "msg": ""}
    request = HTTPRequest(uid=uid)
    resp = request.Request("GetUserRegionApiMaimaiChn", {"userId": uid})

    for i in range(len(resp["userRegionList"])):
        region_name = region_map[int(resp["userRegionList"][i]["regionId"]) - 1]
        resp["userRegionList"][i]["regionName"] = region_name

    result["data"] = resp
    result["is_success"] = True
    result["is_error"] = False
    result["msg"] = "成功"
    return result

def get_user_id_by_qr(qr_code):
    return requests.get(f"{random.choice(config["chime_hosts"])}/api/qr?content={qr_code}").json()