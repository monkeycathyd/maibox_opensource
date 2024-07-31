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

def getLogger(name):
    logging.basicConfig(level=logging.getLevelName(cfg["log"]["level"].upper()), format=cfg["log"]["format"])

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.getLevelName(cfg["log"]["level"].upper()))
    console_handler.setFormatter(logging.Formatter(cfg["log"]["format"]))

    # 创建一个文件处理程序，并将其级别、格式等设置与日志记录器相同
    file_handler = logging.FileHandler('logging.log')
    file_handler.setLevel(logging.getLevelName(cfg["log"]["level"].upper()))
    file_handler.setFormatter(logging.Formatter(cfg["log"]["format"]))

    logger = logging.getLogger(name)

    # 将控制台处理程序和文件处理程序添加到日志记录器中
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger

