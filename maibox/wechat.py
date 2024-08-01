import json
import time

import requests

from maibox.config import get_config
from maibox.utils import getLogger

cfg = get_config()
logger = getLogger(__name__)

class WechatUtils:
    def __init__(self):
        self.limited_mode = cfg["wechat"].get("limited_mode", True)
        self._app_id = cfg["wechat"]["app_id"]
        self._app_secret = cfg["wechat"]["app_secret"]
        self._access_token = {
            "access_token": "",
            "expires_in": 0,
            "timestamp": 0
        }

    def _get_or_update_access_token(self):
        if self._access_token["timestamp"] + self._access_token["expires_in"] > int(round(time.time())):
            return self._access_token["access_token"]
        access_token_api = 'https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={app_id}&secret={app_secret}'.format(app_id=self._app_id, app_secret=self._app_secret)
        response = requests.get(access_token_api)
        if response.status_code != 200:
            return ""
        else:
            self._access_token["access_token"] = response.json()["access_token"]
            self._access_token["expires_in"] = response.json()["expires_in"]
            self._access_token["timestamp"] = int(round(time.time()))
            return self._access_token["access_token"]

    def reply_msg(self, data: dict):
        logger.info(f"Reply msg: {data}")
        if self.limited_mode:
            logger.warning("Limited mode is enabled, reply msg is disabled.")
            return False
        access_token = self._get_or_update_access_token()
        api = "https://api.weixin.qq.com/cgi-bin/message/custom/send?access_token={access_token}".format(access_token=access_token)
        response = requests.post(api, data=json.dumps(data, ensure_ascii=False), headers={"Content-Type": "application/json"})
        logger.info(response.json())
        return response.status_code == 200

    def send_temp_img(self, img_path: str):
        logger.info(f"Send temp img: {img_path}")
        if self.limited_mode:
            logger.warning("Limited mode is enabled, send temp img is disabled.")
            return ""
        access_token = self._get_or_update_access_token()
        api = "https://api.weixin.qq.com/cgi-bin/media/upload?access_token={access_token}&type=image".format(access_token=access_token)
        response = requests.post(api, files={"media": open(img_path, "rb")})
        logger.info(response.json())
        return response.json()["media_id"]

    def send_permanent_img(self, img_path: str):
        logger.info(f"Send permanent img: {img_path}")
        access_token = self._get_or_update_access_token()
        api = "https://api.weixin.qq.com/cgi-bin/material/add_material?access_token={access_token}&type=image".format(access_token=access_token)
        response = requests.post(api, files={"media": open(img_path, "rb")})
        logger.info(response.json())
        return response.json()["media_id"]

    def remove_permanent_img(self, media_id: str):
        logger.info(f"Remove permanent img: {media_id}")
        access_token = self._get_or_update_access_token()
        api = "https://api.weixin.qq.com/cgi-bin/material/del_material?access_token={access_token}".format(access_token=access_token)
        response = requests.post(api, data=json.dumps({"media_id": media_id}, ensure_ascii=False), headers={"Content-Type": "application/json"})
        logger.info(response.json())
        return response.status_code == 200
