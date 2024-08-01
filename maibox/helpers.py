import platform
import random
import re

import time
from datetime import datetime, timedelta

import requests

from maibox import chime
from maibox.HTTPRequest import HTTPRequest
from maibox.config import get_config
from maibox.constants import ticket_define, region_map

config = get_config()

def get_preview(uid, dao):
    result = {"is_success": False, "is_error": False, "user_id": uid, "data":{}, "msg": "", "is_in_whitelist": False}
    if config["settings"]["whitelist"]["enable"] and dao:
        if dao.isWhitelist(uid):
            result["is_in_whitelist"] = True
    else:
        result["is_in_whitelist"] = True
    login_dict = {
        "userId": uid,
        "accessCode": "",
        "regionId": config["arcade_info"]["region_id"],
        "placeId": config["arcade_info"]["place_id"],
        "clientId": config["arcade_info"]["key_chip"],
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
        "regionId": config["arcade_info"]["region_id"],
        "placeId": config["arcade_info"]["place_id"],
        "clientId": config["arcade_info"]["key_chip"],
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
                "placeId": config["arcade_info"]["place_id"],
                "regionId": config["arcade_info"]["region_id"],
                "clientId": config["arcade_info"]["key_chip"],
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
        "placeId": config["arcade_info"]["place_id"],
        "regionId": config["arcade_info"]["region_id"],
        "clientId": config["arcade_info"]["key_chip"],
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

    available_attrs = ["UserData","UserExtend","UserOption","UserCharacter","UserMap","UserLoginBonus","UserRating","UserItem","UserMusic","UserCourse","UserCharge"]
    data = {}

    login_time = int(time.time())

    login_dict = {
        "userId": uid,
        "accessCode": "",
        "regionId": config["arcade_info"]["region_id"],
        "placeId": config["arcade_info"]["place_id"],
        "clientId": config["arcade_info"]["key_chip"],
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
    if len(config["urls"]["chime_hosts"]) > 0:
        return requests.get(f"{random.choice(config["urls"]["chime_hosts"])}/api/qr?content={qr_code}").json()
    if platform.system() != "Windows":
        return {
            "userID": 0,
            "errorID": 88,
            "timestamp": datetime.now().strftime("%Y%m%d%H%M%S")[2:]
        }
    if not(qr_code.startswith("SGWCMAID") and len(qr_code) == 84 and bool(re.match(r'^[0-9A-F]+$', qr_code[20:]))):
        return {
            "userID": 0,
            "errorID": 99,
            "timestamp": datetime.now().strftime("%Y%m%d%H%M%S")[2:],
        }
    getUserData = chime.GetUserData('MAID', 'A63E-01E11910000', '', qr_code[20:])
    while not getUserData.is_end():
        getUserData.execute()
    return {
        "userID": getUserData.get_user_id(),
        "errorID": getUserData.get_error_id(),
        "timestamp": datetime.now().strftime("%Y%m%d%H%M%S")[2:],
    }