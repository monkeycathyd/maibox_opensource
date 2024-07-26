import hashlib
import logging
import random
import re
import string
import threading
import time
import traceback
import uuid
from io import BytesIO

import jieba
import requests
from pyzbar.pyzbar import decode
from PIL import Image

from maibox import auto_bot
from maibox import config
from maibox.automate import ErrorEMailSender
from maibox.ai_chat import ai_chat
from maibox import fish_sync
from maibox.b50gen import call as b50call
from maibox.utils import getLogger
logger = getLogger(__name__)

cfg = config.get_config()
agreement = cfg["agreement"]["text"].replace("{place}", "公众号").replace("{negopt}", "取消关注")

class TextChatHandler:
    def __init__(self, dao):
        self.dao = dao
        self.command_map = {
            '同步': self.handle_sync, #
            '看我': self.handle_preview, #
            '加入白名单': self.handle_whitelist_join, #
            '润': self.handle_logout, #
            '解绑': self.handle_unbind, #
            '绑定': self.handle_bind, #
            '查票': self.handle_query_ticket, #
            '发票': self.handle_send_ticket, #
            '版本': self.handle_version, #
            '帮助': self.handle_help, #
            '使用须知': self.handle_agreement, #
            'admin': self.handle_admin, #
            '足迹': self.handle_region, #
            'b50': self.handle_b50, #
            '解析': self.handle_resolve #
        }
        self.admin_command_map = {
            'log': self.handle_admin_log,
            'whitelist': self.handle_admin_whitelist
        }
        for word in self.command_map.keys():
            jieba.add_word(word)


    def final_word_cut(self,text):
        return [word for word in jieba.lcut(text.strip()) if word not in [" ","\n"]]

    def decode_qr_from_url(self, url):
        # 下载图片
        response = requests.get(url)
        # 将二进制数据转换为图像对象
        img_bytes = BytesIO(response.content)
        image = Image.open(img_bytes)
        # 解码二维码
        decoded_objects = decode(image)
        # 返回解码结果
        if decoded_objects:
            return decoded_objects[0].data.decode('utf-8')
        else:
            return None

    def process_img(self, url, wxid):
        return_msg = ""
        hashed_wxid = hashlib.md5(wxid.encode()).hexdigest().lower()
        qr_content = self.decode_qr_from_url(url)
        if qr_content and ((len(qr_content) == 84) and qr_content.startswith("SGWCMAID") and qr_content[8:20].isdigit() and bool(re.match(r'^[0-9A-F]+$', qr_content[20:]))):
            result = self.getUserIDByQR(qr_content)
            uid = result["userID"]
            eid = result["errorID"]
            if uid and eid == 0:
                resp = auto_bot.get_preview(uid, self.dao)
                if resp["data"]["userId"] and resp["data"]["userName"]:
                    return_msg = f"{resp["data"]["userId"]}: {resp["data"]["userName"]} ({resp["data"]["playerRating"]})\n{self.bind(uid, hashed_wxid)}\n温馨提示：当您取消关注公众号时您的账号绑定关系也会一并清除（不包含白名单记录）"
                else:
                    return_msg = "绑定失败，无法获取到该用户信息，请检查二维码内容是否正确"
            else:
                return_msg = "解析失败，请检查二维码是否正确"
        return return_msg

    def process_event(self, event, wxid, version="", region=""):
        hashed_wxid = hashlib.md5(wxid.encode()).hexdigest().lower()
        return_msg = ""
        match event:
            case "subscribe":
                return_msg = f"""当前版本: {version} ({region})
欢迎关注，{agreement}
发送 “帮助” 以获取使用指引。"""
            case "unsubscribe":
                try:
                    self.unbind(hashed_wxid)
                except:
                    pass
            case _:
                pass

        return return_msg

    def process_chat(self,content, wxid, version="", region=""):
        hashed_wxid = hashlib.md5(wxid.encode()).hexdigest().lower()
        return_msg = ""
        try:
            split_content = self.final_word_cut(content)
            if split_content[0] in self.command_map:
                return_msg = self.command_map[split_content[0]](hashed_wxid, content, version, region)
            else:
                return_msg = self.handle_ai(hashed_wxid, content, version, region)
        except Exception as e:
            return_msg = self.handle_error(wxid, content, version, region, e)
        finally:
            logger.info(f"Hashed User OpenID: {hashed_wxid}")
            logger.info(f"User: {wxid}\nSend: {content}\nResponse: {return_msg}")

        return return_msg


    def handle_error(self, wxid: str, content: str, version: str, region: str, e: BaseException):
        traceback_info = traceback.format_exc()
        err_uuid = uuid.uuid1()
        logger.error(f"Error {err_uuid}: {e}\n{traceback_info}")

        if "incorrect header check" in str(e):
            return_msg = "你wahleak服务器又在胡言乱语力（\n要不再试试？"
        else:
            ErrorEMailSender(f"发生错误: {err_uuid}", f"{e}\n{traceback_info}").start()

            if wxid in cfg["wxid_admins"]:
                return_msg = f"发生错误：{e}\n(错误日志已发送，识别码：{err_uuid})"
            else:
                return_msg = f"发生错误，请联系管理员\n(错误日志已发送，识别码：{err_uuid})"

        return return_msg

    def handle_agreement(self, wxid: str, content: str, version: str, region: str):
        return agreement

    def handle_whitelist_join(self, wxid: str, content: str, version: str, region: str):
        my_preview = self.preview(wxid)
        if not my_preview:
            return_msg = "你还没有绑定，发送 “绑定 [你的UserID]” 绑定"
        else:
            if not my_preview["is_in_whitelist"]:
                return_msg = "请填写白名单登记收集表\nhttps://docs.qq.com/form/page/DTHBDa3N1cXp0dWRM\n\n我们会在48小时内处理该请求。"
            else:
                return_msg = "您已经加入白名单，无需重新申请加入。"

        return return_msg

    def handle_version(self, wxid: str, content: str, version: str, region: str):
        return_msg = f"当前版本: {version} ({region})"
        return return_msg

    def handle_help(self, wxid: str, content: str, version: str, region: str):
        return_msg = ("帮助"
        "\n直接发送带有登入二维码的图片即可解析并绑定UserID"
        "\n发送 “绑定 [你的UserID或二维码内容]” 绑定UserID到微信"
        "\n发送 “润 [UserID]” 解小黑屋（已废弃）"
        "\n发送 “看我” 查看我的信息"
        "\n发送 “解绑” 解绑UserID"
        "\n发送 “解析 [二维码内容]” 解析UserID"
        "\n发送 “发票 [跑图票倍数2-6之间]” 进行发票（限时解禁）"
        "\n发送 “查票” 查询当前跑图票记录"
        "\n发送 “足迹” 查看当前出勤地区记录"
        "\n发送 “同步” 同步当前乐曲数据到水鱼查分器"
        "\n发送 “b50” 生成B50图片"
        "\n发送 “加入白名单” 以获取指引"
        "\n发送 “使用须知” 以查阅条款内容"
        "\n"
        "\n当前版本: {version} ({region})")

        return return_msg.format(version=version, region=region)

    def handle_bind(self, wxid: str, content: str, version: str, region: str):
        split_content = self.final_word_cut(content)
        if len(split_content) == 2:
            if split_content[-1].isdigit():  # 如果是User ID
                resp = auto_bot.get_preview(int(split_content[-1]), self.dao)
                if resp["data"]["userId"] and resp["data"]["userName"]:
                    return_msg = f"{resp["data"]["userId"]}: {resp["data"]["userName"]} ({resp["data"]["playerRating"]})\n{self.bind(split_content[-1], wxid)}\n温馨提示：当您取消关注公众号时您的账号绑定关系也会一并清除（不包含白名单记录）"
                else:
                    return_msg = "绑定失败，无法获取到该用户信息，请检查UserID是否正确"
            elif split_content[-1].startswith("SGWCMAID"):  # 如果是二维码
                result = self.getUserIDByQR(split_content[1])
                uid = result["userID"]
                eid = result["errorID"]
                if uid and eid == 0:
                    resp = auto_bot.get_preview(uid, self.dao)
                    if resp["data"]["userId"] and resp["data"]["userName"]:
                        return_msg = f"{resp["data"]["userId"]}: {resp["data"]["userName"]} ({resp["data"]["playerRating"]})\n{self.bind(uid, wxid)}\n温馨提示：当您取消关注公众号时您的账号绑定关系也会一并清除（不包含白名单记录）"
                    else:
                        return_msg = "绑定失败，无法获取到该用户信息，请检查二维码内容是否正确"
                else:
                    return_msg = "解析失败，请检查二维码是否正确"
            else:
                return_msg = "内容错误，发送 “绑定 [你的UserID或二维码内容]” 绑定"
        else:
            return_msg = "未指定UserID，发送 “绑定 [你的UserID或二维码内容]” 绑定"
        return return_msg
    def handle_unbind(self, wxid: str, content: str, version: str, region: str):
        return self.unbind(wxid)

    def handle_logout(self, wxid: str, content: str, version: str, region: str):
        split_content = self.final_word_cut(content)
        if len(split_content) == 3:
            return_msg = auto_bot.logout(int(split_content[1]), int(split_content[2]))["msg"]
        else:
            blackroom = self.blackroom(wxid, int(split_content[1]))
            if blackroom:
                return_msg = blackroom
            else:
                return_msg = "未绑定或未指定UserID，发送 “绑定 [你的UserID]” 绑定或发送 “润 [UserID] [秒级Unix时间戳]” 解小黑屋"
        return return_msg

    def handle_preview(self, wxid: str, content: str, version: str, region: str):
        my_preview = self.preview(wxid)
        return_msg = ""
        if not my_preview:
            return_msg = "未绑定，发送 “绑定 [你的UserID]” 绑定"
        if isinstance(my_preview, str):
            return_msg = my_preview
        elif isinstance(my_preview, dict):
            last_game_data_character = int(my_preview["data"]["lastDataVersion"].split(".")[-1])
            last_rom_ver_tuple = tuple(map(int, my_preview["data"]["lastRomVersion"].split(".")))
            last_data_ver_tuple = tuple(map(int, my_preview["data"]["lastDataVersion"].split(".")))
            return_msg = f"""
{"警告！用户游戏版本异常" if (last_data_ver_tuple[0] != 1 and last_data_ver_tuple[1] % 5 != 0) or (last_rom_ver_tuple[0] != 1 and last_rom_ver_tuple[2] != 0) else ""}
微信用户ID（已哈希化）: {wxid}
用户ID: {my_preview["data"]["userId"]}
昵称: {my_preview["data"]["userName"]}
游戏Rating: {my_preview["data"]["playerRating"]}
上次游戏版本：CN{".".join(my_preview["data"]["lastRomVersion"].split(".")[0:2])}{f"-{chr(ord("A") - 1 + last_game_data_character)}" if last_game_data_character > 0 else ""}
封禁状态: {["正常", "警告", "封禁"][my_preview["data"]["banState"]]}
你当前{"正在" if my_preview["data"]["isLogin"] else "未"}上机
{"你当前是受邀用户" if my_preview["is_in_whitelist"] else ""}""".strip()

        return return_msg

    def handle_resolve(self, wxid: str, content: str, version: str, region: str):
        split_content = self.final_word_cut(content)
        if len(split_content) != 2:
            return_msg = "发送 “解析 [二维码内容]” 解析UserID"
        else:
            result = self.getUserIDByQR(split_content[1])
            uid = result["userID"]
            eid = result["errorID"]
            if uid and eid == 0:
                return_msg = f"解析成功，UserID: {uid}\n请发送 “绑定 {uid}” 以绑定该UserID"
            else:
                return_msg = "解析失败，请检查二维码是否正确"
        return return_msg

    def handle_send_ticket(self, wxid: str, content: str, version: str, region: str):
        split_content = self.final_word_cut(content)
        user_id = self.dao.getUid(wxid)
        my_preview = self.preview(wxid)
        if isinstance(my_preview, dict):
            if my_preview["is_in_whitelist"] or True:
                if 6 >= int(split_content[1]) >= 2:
                    return_msg = auto_bot.send_ticket(user_id, int(split_content[1]))["msg"]
                else:
                    return_msg = "倍数不在2-6之间"
            else:
                return_msg = "你没有权限，发送 “加入白名单” 以获取指引"
        else:
            return_msg = my_preview

        return return_msg

    def handle_query_ticket(self, wxid: str, content: str, version: str, region: str):
        uid = self.dao.getUid(wxid)
        data = auto_bot.query_ticket(uid)
        message = f"用户ID: {data["data"]["userId"]}\n倍券类型数量: {data["data"]["length"]}\n倍券列表:\n"
        for i in range(len(data["data"]["userChargeList"])):
            message += f"""
{i + 1}. 倍券ID：{data["data"]["userChargeList"][i]["chargeId"]}
当前持有{data["data"]["userChargeList"][i]["stock"]}张，最近一次购买于{data["data"]["userChargeList"][i]["purchaseDate"]}，有效期至{data["data"]["userChargeList"][i]["validDate"]}"""
        return_msg = message
        return return_msg

    def handle_sync(self, wxid: str, content: str, version: str, region: str):
        split_content = self.final_word_cut(content)
        return_msg = ""
        flag = False
        uid = self.dao.getUid(wxid)
        username, password = self.dao.get_df_account(wxid)
        if username and password:
            return_msg += f"水鱼账户: {username}\n"
            if len(split_content) == 2 and split_content[1] == "解绑":
                self.dao.unbind_df(wxid)
                return_msg += "解绑成功"
            else:
                flag = True
        else:
            if len(content.split(" ")) != 3:
                return_msg += "发送 “同步 [用户名] [密码]” 以绑定水鱼账户"
            else:
                username, password = content.split(" ")[1:]
                self.dao.bind_df(wxid, username, password)
                return_msg += "绑定成功，发送 “同步 解绑” 以解绑水鱼账户，发送 “同步” 以同步乐曲数据到水鱼查分器\n"
                flag = True
        if flag:
            if fish_sync.update_fish(username, password, uid):
                return_msg += "同步成功"
            else:
                return_msg += "同步失败，请检查用户名和密码是否正确"
        return return_msg

    def handle_b50(self, wxid: str, content: str, version: str, region: str):
        return self.b50(wxid)

    def handle_region(self, wxid: str, content: str, version: str, region: str):
        return self.region(wxid)

    def handle_ai(self, wxid: str, content: str, version: str, region: str):
        return ai_chat(content.strip())

    def handle_admin(self, wxid: str, content: str, version: str, region: str):
        split_content = self.final_word_cut(content)
        return_msg = ""
        if wxid not in cfg["wxid_admins"]:
            return_msg = ai_chat(content.strip())
        else:
            if len(split_content) > 1 and split_content[1] in self.admin_command_map:
                return_msg = self.admin_command_map[split_content[1]](content)
            else:
                return_msg = "行为未定义"

        return return_msg

    def handle_admin_log(self, content: str):
        ErrorEMailSender("实时日志", "").start()
        return "日志将在稍后发送"

    def handle_admin_whitelist(self, content: str):
        split_content = self.final_word_cut(content)
        return_msg = ""
        if len(split_content) == 2:
            whitelist = self.dao.getAllWhitelist()
            if whitelist:
                return_msg = "\n".join(whitelist)
                return_msg += f"\nlength: {len(whitelist)}"
            else:
                return_msg = "白名单为空"
        elif split_content[2] == "add":
            resp = auto_bot.get_preview(int(split_content[-1]), self.dao)
            if resp["data"]["userId"] and resp["data"]["userName"]:
                return_msg = f"{resp["data"]["userId"]}: {resp["data"]["userName"]} ({resp["data"]["playerRating"]})\n"
                if self.dao.addWhitelist(int(split_content[3])):
                    return_msg += "添加成功"
                else:
                    return_msg += "添加失败"
        elif split_content[2] == "remove":
            resp = auto_bot.get_preview(int(split_content[-1]), self.dao)
            if resp["data"]["userId"] and resp["data"]["userName"]:
                return_msg = f"{resp["data"]["userId"]}: {resp["data"]["userName"]} ({resp["data"]["playerRating"]})\n"
                if self.dao.removeWhitelist(int(split_content[3])):
                    return_msg += "删除成功"
                else:
                    return_msg += "删除失败"
        else:
            whitelist = self.dao.getAllWhitelist()
            if whitelist:
                return_msg = "\n".join(whitelist)
                return_msg += f"\nlength: {len(whitelist)}"
            else:
                return_msg = "白名单为空"
        return return_msg




    def isWhitelist(self, wxid: str) -> bool:
        uid = self.dao.getUid(wxid)
        return self.dao.isWhitelist(uid)

    def bind(self,uid,wxid):
        bind = self.dao.bind(uid, wxid)
        if bind:
            return "绑定成功，如需解绑，发送 “解绑” 解绑"
        else:
            return "绑定失败，您已经绑定过UserID，如需解绑，发送 “解绑” 解绑"

    def unbind(self,wxid):
        unbind = self.dao.unbind(wxid)
        if unbind:
            return "解绑成功"
        else:
            return "解绑失败"

    def blackroom(self,wxid, timestamp):
        uid = self.dao.getUid(wxid)
        if uid:
            try:
                return auto_bot.logout(uid, timestamp)["msg"]
            except Exception as e:
                logger.error(f"Error {uuid.uuid1()}: {e}")
                return "访问失败，可能是服务器错误"
        else:
            return None

    def preview(self,wxid):
        uid = self.dao.getUid(wxid)
        if uid:
            try:
                return auto_bot.get_preview(uid, self.dao)
            except Exception as e:
                logger.error(f"Error {uuid.uuid1()}: {e}")
                return "访问失败，可能是服务器错误"
        else:
            return None

    def region(self,wxid):
        uid = self.dao.getUid(wxid)
        if uid:
            try:
                user_region = auto_bot.get_user_region(uid)["data"]
                text = f"你目前一共在{user_region["length"]}个地区出过勤: \n"
                for i in range(len(user_region["userRegionList"])):
                    text += f"\n{i+1}.{user_region["userRegionList"][i]['regionName']} 玩过{user_region["userRegionList"][i]['playCount']}次 首次记录于{user_region["userRegionList"][i]['created']}"
                return text
            except Exception as e:
                logger.error(f"Error {uuid.uuid1()}: {e}")
                return "访问失败，可能是服务器错误"
        else:
            return None

    def getUserIDByQR(self, qr_code):
        if (len(qr_code) == 84) and qr_code.startswith("SGWCMAID") and qr_code[8:20].isdigit() and bool(re.match(r'^[0-9A-F]+$', qr_code[20:])):
            return auto_bot.get_user_id_by_qr(qr_code)
        else:
            return None

    def b50(self, wxid):
        return_msg = ""
        username, password = self.dao.get_df_account(wxid)
        uid = self.dao.getUid(wxid)
        preview = auto_bot.get_preview(uid, self.dao)
        nickname = preview["data"]["userName"]
        icon_id = preview["data"]["iconId"]
        if username and password:
            return_msg += f"水鱼账户: {username}\n"
            if fish_sync.update_fish(username, password, uid):
                return_msg += "水鱼同步成功\n"
            else:
                return_msg += "水鱼同步失败，请检查用户名和密码是否正确"
        else:
            return_msg += "未绑定水鱼账户，发送“同步 [用户名] [密码]”以绑定水鱼账户\n"
            return return_msg
        file_id = hashlib.md5(
            f"{wxid}_{int(time.time())}_{"".join(random.sample(string.ascii_letters + string.digits, 8))}".encode()).hexdigest().lower()
        filename = f"b50_{file_id}.jpg"
        threading.Thread(target=b50call, args=(username, filename, nickname, icon_id,)).start()
        return_msg += f"b50图片获取地址：\n{cfg["api_url"]}/img/b50?id={file_id}\n图片文件随时可能会被删除，还请尽快下载"
        return return_msg
