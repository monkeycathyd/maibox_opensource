import hashlib
import logging

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

    file_handler = logging.FileHandler("logging.log", encoding="utf-8")
    file_handler.setFormatter(logging.Formatter(cfg["log"]["format"]))
    file_handler.setLevel(logging.getLevelName(cfg["log"]["level"].upper()))
    logger.addHandler(file_handler)

    return logger

def get_version_label(code: int, string: str=""):
    if code == 0:
        return string
    code = code - 1
    if code // 26 == 0:
        return string + chr(code % 26 + ord('A'))
    return get_version_label(code // 26 - 1, string + chr(code % 26 + ord('A')))

def find_chara_levels(all_chara_list, chara_slot_list):
    """
    根据角色槽列表，从所有角色列表中找出对应角色的等级。

    :param all_chara_list: 包含所有角色信息的列表，每个元素是一个字典，必须包含"characterId"和"level"键。
    :param chara_slot_list: 包含角色槽ID的列表，用于查找对应角色的等级。
    :return: 一个整数列表，表示对应角色槽的角色等级。如果某个角色槽没有对应的角色，则该位置的等级为0。
    """
    # 初始化角色等级列表，长度与chara_slot_list相同
    character_levels = [0] * len(chara_slot_list)
    # {"characterId":101,"point":0,"useCount":2147483647,"level":9999,"nextAwake":0,"nextAwakePercent":0,"awakening":6}
    # 创建一个角色ID到等级的映射，以提高查找效率
    chara_id_to_level = {}
    for chara in all_chara_list:
        chara_id = chara.get("characterId")
        level = chara.get("level")
        if chara_id is not None and level is not None:
            chara_id_to_level[chara_id] = int(level)

    # 使用映射更新角色槽的等级信息
    for i, chara_slot in enumerate(chara_slot_list):
        level = chara_id_to_level.get(chara_slot)
        if level is not None:
            character_levels[i] = level

    return character_levels

def find_chara_awakening(all_chara_list, chara_slot_list):
    """
    根据角色槽列表，从所有角色列表中找出对应角色的觉醒数。

    :param all_chara_list: 包含所有角色信息的列表，每个元素是一个字典，必须包含"characterId"和"level"键。
    :param chara_slot_list: 包含角色槽ID的列表，用于查找对应角色的等级。
    :return: 一个整数列表，表示对应角色槽的角色等级。如果某个角色槽没有对应的角色，则该位置的等级为0。
    """
    # 初始化角色等级列表，长度与chara_slot_list相同
    character_awakening = [0] * len(chara_slot_list)
    # {"characterId":101,"point":0,"useCount":2147483647,"level":9999,"nextAwake":0,"nextAwakePercent":0,"awakening":6}
    # 创建一个角色ID到等级的映射，以提高查找效率
    chara_id_to_level = {}
    for chara in all_chara_list:
        chara_id = chara.get("characterId")
        awakening = chara.get("awakening")
        if chara_id is not None and awakening is not None:
            chara_id_to_level[chara_id] = int(awakening)

    # 使用映射更新角色槽的等级信息
    for i, chara_slot in enumerate(chara_slot_list):
        awakening = chara_id_to_level.get(chara_slot)
        if awakening is not None:
            character_awakening[i] = awakening

    return character_awakening