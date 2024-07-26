import hashlib
import logging
import time

from maibox.config import get_config

cfg = get_config()

def check_wx_auth(wx_auth):
    """timestamp,random_string,md5_hashed_string <== wx_auth
        md5_hashed_string ==> timestamp,random_string,token
        token is in config.wx_token
    """
    print("get wx auth", wx_auth)
    wx_token = cfg["wechat_token"]
    if wx_token == "" or wx_auth == "":
        return False
    splited_auth = wx_auth.split(",")
    if len(splited_auth) != 3:
        return False
    ctime = int(time.time() * 1000)
    if int(splited_auth[0]) + 60000 < ctime:
        return False
    calc_auth = hashlib.md5(f"{splited_auth[0]},{splited_auth[1]},{wx_token}".encode("utf-8")).hexdigest().lower()
    print("calc auth", calc_auth)
    if splited_auth[2] != calc_auth:
        return False
    return True

def getLogger(name):
    logging.basicConfig(level=logging.getLevelName(cfg["log_level"].upper()), format=cfg["log_format"])

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(logging.Formatter(cfg["log_format"]))

    # 创建一个文件处理程序，并将其级别、格式等设置与日志记录器相同
    file_handler = logging.FileHandler(f'logging.log')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(cfg["log_format"]))

    logger = logging.getLogger(name)

    # 将控制台处理程序和文件处理程序添加到日志记录器中
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger

