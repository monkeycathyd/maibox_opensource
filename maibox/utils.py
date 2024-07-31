import hashlib
import logging
import time

from maibox.config import get_config

cfg = get_config()

def check_wx_auth(signature, timestamp, nonce):
    token = cfg["wechat"]["token"]
    auth_list = [token, timestamp, nonce]
    auth_list.sort()
    sha1 = hashlib.sha1()
    sha1.update(auth_list[0].encode('utf-8'))
    sha1.update(auth_list[1].encode('utf-8'))
    sha1.update(auth_list[2].encode('utf-8'))
    hashcode = sha1.hexdigest()
    return hashcode == signature

def is_hex_string(s):
    return all(c in {'e', '4', '1', '6', '7', 'c', '8', '2', '0', '5', 'b', 'd', 'a', 'f', '9', '3'} for c in s)

def getLogger(name):
    logging.basicConfig(level=logging.getLevelName(cfg["log"]["level"].upper()), format=cfg["log"]["format"])
    logger = logging.getLogger(name)
    logger.addHandler(logging.StreamHandler())
    logger.addHandler(logging.FileHandler('logging.log'))
    return logger

