import hashlib
import json
import logging
import time
import zlib
import random

import urllib3

import maibox.config as config
from maibox.crypto import CipherAES
from maibox.SocketHttps import HttpClient
from maibox.utils import getLogger

cfg = config.get_config()

logger = getLogger(__name__)

class HTTPRequest:
    def __init__(self, uid=-1):
        self._title_server_uri = random.choice(cfg["title_server_url"])
        self._obfuscate_param = cfg["obfuscate_param"]
        # self._title_server_uri = cfg["title_server_url"][0]
        self._key_chip = cfg["key_chip"]
        self._timeout = cfg["request_timeout"]
        self._max_retry = cfg["request_retry_times"]
        self._uid = uid
        self._mai_encoding = cfg["mai_encoding"]

    @staticmethod
    def obfuscator(param: str) -> str:
        return hashlib.md5(str.encode(param + HTTPRequest()._obfuscate_param)).hexdigest()

    def Request(self, api: str, datas: dict):
        if not (api.endswith("MaimaiChn")):
            api += "MaimaiChn"
        unobfuscated_api = api

        api = self.obfuscator(api)
        url = self._title_server_uri + api

        final_data  = zlib.compress(CipherAES.encrypt(json.dumps(datas).encode("utf-8")))
        header = {
            "Content-Type": "application/json",
            "User-Agent": f"{api}#{self._key_chip if self._uid == -1 else self._uid}",
            "charset": "UTF-8",
            "Mai-Encoding": self._mai_encoding,
            "Content-Encoding": "deflate",
            "Content-Length": str(len(final_data)),
            "Host": urllib3.util.parse_url(self._title_server_uri).host,
        }
        logger.info(f"Requesting {unobfuscated_api}:\nRequest URL:{url}\nRequest Data:{datas}\nRequest Header:{header}")

        result = {"status_code": 400, "headers": {}, "body": b""}
        ctime = int(round(time.time() * 1000))
        for i in range(self._max_retry):
            result = HttpClient.post(urllib3.util.parse_url(url), header, final_data.strip(), float(self._timeout))
            if result["status_code"] != 200:
                continue
            if len(result["body"]) > 0:
                break

        if not (len(result["body"]) > 0):
            raise Exception("Max Retry Failed")
        if result["status_code"] != 200:
            raise Exception(f"Request Failed with status code {result['status_code']}")

        end = int(round(time.time() * 1000)) - ctime
        logger.info(f"{unobfuscated_api} was response in {end}ms:\nStatus Code: {result['status_code']}\nHeaders: {result['headers']}")
        try:
            final_content = json.loads(CipherAES.decrypt(zlib.decompress(result["body"])))
            logger.info(f"{unobfuscated_api} Response data: {final_content}")
            return final_content
        except Exception as e:
            logger.error(f"{unobfuscated_api} was error in decoding with\n{result["body"]}")
            raise e
