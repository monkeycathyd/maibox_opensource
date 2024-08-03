import json
import time
import os
import random
import re
import hashlib

import requests
requests.packages.urllib3.disable_warnings()

from maibox.config import get_config
from maibox.utils import getLogger

cfg = get_config()
logger = getLogger(__name__)

class CommonUtil:

    @staticmethod
    def md5(text):
        hl = hashlib.md5()
        hl.update(text.encode(encoding='utf-8'))
        return hl.hexdigest()

    @staticmethod
    def str_join(arr, separator=","):
        if arr.__len__() == 1:
            return str(arr)
        return separator.join(arr)

class WechatInterface:
    def send_text(self, text: str, wxid: str):
        pass

    def send_image(self, path: str, wxid: str):
        pass

    def interface_test(self):
        return False

class WechatOfficialUtils(WechatInterface):
    def __init__(self):
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

    def send_text(self, text: str, wxid: str):
        logger.info(f"Send text: {text}")
        self.reply_msg({
            "touser": wxid,
            "msgtype": "text",
            "text":{
                "content": text
            }
        })

    def send_image(self, path: str, wxid: str):
        logger.info(f"Send image: {path}")
        self.reply_msg({
            "touser": wxid,
            "msgtype": "image",
            "image": {
                "media_id": str(self.send_temp_img(path))
            }
        })

    def interface_test(self):
        return self._get_or_update_access_token() != ""

    def reply_msg(self, data: dict):
        logger.info(f"Reply msg: {data}")
        access_token = self._get_or_update_access_token()
        api = "https://api.weixin.qq.com/cgi-bin/message/custom/send?access_token={access_token}".format(access_token=access_token)
        response = requests.post(api, data=json.dumps(data, ensure_ascii=False), headers={"Content-Type": "application/json"})
        logger.info(response.json())
        return response.status_code == 200

    def send_temp_img(self, img_path: str):
        logger.info(f"Send temp img: {img_path}")
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

class WechatUnofficialUtils(WechatInterface):

    def __init__(self):
        self.session = requests.session()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.80 Safari/537.36',
            'Referer': 'https://mp.weixin.qq.com/'
        }
        self.QRImgPath = './webWeixinQr.jpg'
        self.token = ""
        self.ticket = ""
        self.fakeid = ""
        self.username = ""
        self.password = ""

    @staticmethod
    def login():
        self = WechatUnofficialUtils()
        self.username = input("请输入您的公众号微信号或邮箱:")
        self.password = input("请输入您的公众号密码:")
        url = "https://mp.weixin.qq.com/cgi-bin/bizlogin?action=startlogin"
        params = {
            'username': self.username,
            'pwd': CommonUtil.md5(self.password),
            'imgcode': '',
            'f': 'json'
        }
        response = self.session.post(url, data=params, headers=self.headers, verify=False)
        if response.status_code != 200:
            return None
        target = response.content.decode('utf-8')
        print(target)
        url = "https://mp.weixin.qq.com/cgi-bin/loginqrcode?action=getqrcode&param=4300"
        response = self.session.get(url, headers=self.headers, verify=False)
        self.tip = 1
        with open(self.QRImgPath, 'wb') as f:
            f.write(response.content)
            f.close()
        print('请打开二维码“webWeixinQr.jpg”，使用微信扫描二维码登录')
        while True:
            url = "https://mp.weixin.qq.com/cgi-bin/loginqrcode?action=ask&token=&lang=zh_CN&f=json&ajax=1"
            response = self.session.get(url, headers=self.headers, verify=False)
            _json = json.loads(response.text)
            if _json["status"] == 1:
                os.remove(self.QRImgPath)
                break
            time.sleep(1)
        url = "https://mp.weixin.qq.com/cgi-bin/bizlogin?action=login"
        data = {
            'f': 'json',
            'ajax': 1,
            'random': random.random()
        }
        response = self.session.post(url, data=data, headers=self.headers, verify=False)
        _json = json.loads(response.text)
        redirect_url = _json["redirect_url"]
        self.token = redirect_url[redirect_url.rfind("=") + 1:len(redirect_url)]
        with open("cookies.json", "w") as f:
            cookies = {
                "account": {
                    "username": self.username,
                    "password": self.password
                },
                "cookies": self.session.cookies.get_dict(),
                "token": self.token
            }
            f.write(json.dumps(cookies, indent=2))

        self._init_self_information()

        return self

    @staticmethod
    def cookie_login(dumped_dict: dict):
        try:
            if not dumped_dict:
                return None
            self = WechatUnofficialUtils()
            self.session.cookies.update(dumped_dict["cookies"])
            self.token = dumped_dict["token"]
            self.username = dumped_dict["account"]["username"]
            self.password = dumped_dict["account"]["password"]
            self._init_self_information()
        except:
            return None

        return self

    def _init_fakeid(self):
        """
        初始化公众号自身的 ``fakeid`` 值
        :raises NeedLoginError: 操作未执行成功, 需要再次尝试登录, 异常内容为服务器返回的错误数据
        """
        if not self.fakeid:
            self._init_self_information()

    def _init_ticket(self):
        """
        初始化公众号自身的 ``ticket`` 及 ``ticket_id`` 值
        :raises NeedLoginError: 操作未执行成功, 需要再次尝试登录, 异常内容为服务器返回的错误数据
        """
        if not self.ticket:
            self._init_self_information()

    def _init_self_information(self):
        """
        初始化公众号自身的属性值 (目前包括 ``Ticket`` 值 及 公众号自身的 ``fakeid`` 值)
        :raises NeedLoginError: 操作未执行成功, 需要再次尝试登录, 异常内容为服务器返回的错误数据
        """
        url = 'https://mp.weixin.qq.com/cgi-bin/home?t=home/index&lang=zh_CN&token={token}'.format(token=self.token)
        headers = {
            'x-requested-with': 'XMLHttpRequest',
            'referer': 'https://mp.weixin.qq.com',
        }
        r = self.session.get(url, headers=headers)

        # 获取 Ticket ID 值
        ticket_id = re.search(r'user_name: \"(.*)\"', r.text)
        if not ticket_id:
            raise Exception(r.text)
        self.ticket_id = ticket_id.group(1)

        # 获取 Ticket 值
        ticket = re.search(r'ticket: \"(.*)\"', r.text)
        if not ticket:
            raise Exception(r.text)
        self.ticket = ticket.group(1)

        # 获取公众号自身的 fakeid 值
        fakeid = re.search(r'uin: \"(.*)\"', r.text)
        if not fakeid:
            raise Exception(r.text)
        self.fakeid = fakeid.group(1)

    def interface_test(self):
        try:
            self._init_self_information()
            return True
        except:
            return False

    def send_text(self, text: str, wxid: str):
        if self.token == "":
            return False
        url = "https://mp.weixin.qq.com/cgi-bin/singlesend?t=ajax-response&f=json"
        data = {
            "tofakeid": wxid,
            "quickreplyid": "500009951",
            "imgcode": "",
            "type": "1",
            "content": text,
            "token": self.token,
            "lang": "zh_CN",
            "f": "json",
            "ajax": "1",
        }
        response = self.session.post(url, data=data, headers=self.headers, verify=False)
        if response.status_code != 200:
            return False
        return response.json()["base_resp"]["ret"] == 0

    def upload_file(self, filepath):
        self._init_ticket()
        url = 'https://mp.weixin.qq.com/cgi-bin/filetransfer?action=upload_material&f=json&ticket_id={ticket_id}&ticket={ticket}&token={token}&lang=zh_CN'.format(
            ticket_id=self.ticket_id,
            ticket=self.ticket,
            token=self.token,
        )
        try:
            files = {'file': open(filepath, 'rb')}
        except IOError:
            raise ValueError('file not exist')
        payloads = {
            'Filename': filepath,
            'folder': '/cgi-bin/uploads',
            'Upload': 'Submit Query',
        }
        headers = {
            'referer': 'http://mp.weixin.qq.com/cgi-bin/indexpage?t=wxm-upload&lang=zh_CN&type=2&formId=1',
        }
        r = self.session.post(url, files=files, data=payloads, headers=headers)

        message = json.loads(r.text)

        return message['content']

    def remove_file(self, file_id):
        api = "https://mp.weixin.qq.com/cgi-bin/modifyfile?t=ajax-response"
        data = {
            "oper": "del",
            "fileid": file_id,
            "copyright_status": "0",
            "group_id": "1",
            "token": self.token,
            "lang": "zh_CN",
            "f": "json",
            "ajax": "1"
        }
        response = self.session.post(api, data=data, headers=self.headers, verify=False)
        return response.status_code == 200

    def send_file(self, fakeid, fid, type):
        if type == 4:  # 此处判断为兼容历史版本, 微信官方已经将视频类型修改为 15
            type = 15

        url = 'https://mp.weixin.qq.com/cgi-bin/singlesend?t=ajax-response&f=json&token={token}&lang=zh_CN'.format(
            token=self.token,
        )
        payloads = {}
        if type == 2 or type == 3:  # 如果文件类型是图片或者音频
            payloads = {
                'token': self.token,
                'lang': 'zh_CN',
                'f': 'json',
                'ajax': 1,
                'random': random.random(),
                'type': type,
                'file_id': fid,
                'tofakeid': fakeid,
                'fileid': fid,
                'imgcode': '',
            }
        elif type == 15:  # 如果文件类型是视频
            payloads = {
                'token': self.token,
                'lang': 'zh_CN',
                'f': 'json',
                'ajax': 1,
                'random': random.random(),
                'type': type,
                'app_id': fid,
                'tofakeid': fakeid,
                'appmsgid': fid,
                'imgcode': '',
            }
        headers = {
            'referer': 'https://mp.weixin.qq.com/cgi-bin/singlesendpage?tofakeid={fakeid}&t=message/send&action=index&token={token}&lang=zh_CN'.format(
                fakeid=fakeid,
                token=self.token,
            ),
            'x-requested-with': 'XMLHttpRequest',
        }
        response = self.session.post(url, data=payloads, headers=headers)

        return response.json()["base_resp"]["ret"] == 0

    def send_image(self, path: str, wxid: str):
        file_id = self.upload_file(path)
        result = self.send_file(wxid, file_id, 2)
        self.remove_file(file_id)
        return result

def get_utils() -> WechatInterface:
    use_interface = cfg["wechat"].get("interact_interface", "")
    interface = WechatInterface()
    if use_interface == "official":
        interface = WechatOfficialUtils()
    elif use_interface == "unofficial":
        try:
            cookies = json.loads(cfg["wechat"].get("unofficial_cookies_json", ""))
            interface = WechatUnofficialUtils.cookie_login(cookies)
        except:
            interface = WechatInterface()
    elif use_interface == "limited":
        interface = WechatInterface()
    if interface.interface_test():
        return interface
    else:
        return WechatInterface()
