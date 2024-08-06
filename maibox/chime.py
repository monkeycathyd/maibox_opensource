import datetime
import hashlib
import random

import requests

from maibox.config import get_config

cfg = get_config()

def get_user_id(qr_code):
    GAME_ID = "MAID"
    AIME_SALT = cfg["crypto"]["chime_salt"]
    if len(cfg["urls"]["chime_hosts"]) > 0:
        AIME_HOST = random.choice(cfg["urls"]["chime_hosts"])
    else:
        AIME_HOST = "http://ai.sys-all.cn"

    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")[2:]
    chip_id = "A63E-01E{0:08}".format(random.randint(0, 99999999))
    key = hashlib.sha256(f"{chip_id}{timestamp}{AIME_SALT}".encode()).hexdigest().upper()
    data_json = f"{{\"chipID\":\"{chip_id}\",\"openGameID\":\"{GAME_ID}\",\"key\":\"{key}\",\"qrCode\":\"{qr_code}\",\"timestamp\":\"{timestamp}\"}}"

    resp = requests.post(f"{AIME_HOST}/wc_aime/api/get_data", data_json, headers={
        "User-Agent": "WC_AIME_LIB",
    })
    return resp.json()



