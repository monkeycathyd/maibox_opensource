import datetime
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

import maibox
from maibox import helpers
from maibox import config
from maibox.process_threads import ErrorEMailSender
from maibox.ai_chat import ai_chat
from maibox import fish_sync
from maibox.generate_img import call_b50, call_user_img, call_user_img_preview
from maibox.utils import getLogger, get_version_label
from maibox.wechat import get_utils

logger = getLogger(__name__)

cfg = config.get_config()
agreement = cfg["agreement"]["text"].format(place="公众号", negopt="取消关注")

class TextChatHandler:
    def __init__(self, dao):
        self.dao = dao
        self._wechat_utils = get_utils()
        self._limited_mode = self._wechat_utils.interface_test()
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
        text = text.replace("\n", " ").replace("[", " ").replace("]", " ")
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

    def process(self, data, version, region):
        msg = ""
        if data["MsgType"] == "event":
            msg = self.process_event(data["Event"], data["FromUserName"], version, region)
        elif data["MsgType"] == "image":
            msg = self.process_img(data["PicUrl"], data["FromUserName"])
        elif data["MsgType"] == "text":
            msg = self.process_chat(data["Content"], data["FromUserName"], version, region)

        return_msg = {
            "FromUserName": data["ToUserName"],
            "ToUserName": data["FromUserName"],
            "CreateTime": int(time.time()),
            "MsgType": "",
            "Content": ""
        }
        if isinstance(msg, str):
            return_msg["MsgType"] = "text"
            return_msg["Content"] = msg
        elif isinstance(msg, dict):
            return_msg = msg
            return_msg["FromUserName"] = data["ToUserName"]
            return_msg["ToUserName"] = data["FromUserName"]
            return_msg["CreateTime"] = int(time.time())

        return return_msg

    def process_img(self, url, wxid):
        return_msg = ""
        hashed_wxid = hashlib.md5(wxid.encode()).hexdigest().lower()
        qr_content = self.decode_qr_from_url(url)
        if 4 <= int(time.strftime("%H")) < 7:
            return "服务器维护期间暂停对外服务，请于北京时间7:00后再试"
        if qr_content and ((len(qr_content) == 84) and qr_content.startswith("SGWCMAID") and qr_content[8:20].isdigit() and bool(re.match(r'^[0-9A-F]+$', qr_content[20:]))):
            result = self.getUserIDByQR(qr_content)
            uid = result["userID"]
            eid = result["errorID"]
            if uid and eid == 0:
                resp = helpers.get_preview(uid, self.dao)
                if resp["data"]["userId"] and resp["data"]["userName"]:
                    return_msg = "{userId}: {userName} ({playerRating})\n{result}\n温馨提示：当您取消关注公众号时您的账号绑定关系也会一并清除（不包含白名单记录）".format(
                        userId=resp["data"]["userId"],
                        userName=resp["data"]["userName"],
                        playerRating=resp["data"]["playerRating"],
                        result=self.bind(uid, hashed_wxid)
                    )
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
                return_msg = "当前版本: {version}-{git} ({region})\n欢迎关注，{agreement}\n发送 “帮助” 以获取使用指引。".format(
                    version=version,
                    region=region,
                    agreement=agreement,
                    git=maibox.git_sha
                )
            case "unsubscribe":
                try:
                    self.unbind(hashed_wxid)
                except:
                    pass
            case _:
                pass

        return return_msg

    def process_chat(self,content, wxid, version="", region=""):
        if 4 <= int(time.strftime("%H")) < 7:
            return "服务器维护期间暂停对外服务，请于北京时间 7:00 后再试"
        hashed_wxid = hashlib.md5(wxid.encode()).hexdigest().lower()
        return_msg = ""
        try:
            split_content = self.final_word_cut(content)
            if split_content[0] in self.command_map:
                return_msg = self.command_map[split_content[0]](hashed_wxid, content, version, region, wxid)
            else:
                return_msg = self.handle_ai(hashed_wxid, content, version, region, wxid)
        except Exception as e:
            return_msg = self.handle_error(hashed_wxid, content, version, region, wxid, e)
        finally:
            logger.info(f"Hashed User OpenID: {hashed_wxid}")
            logger.info(f"User: {wxid}\nSend: {content}\nResponse: {return_msg}")

        self._limited_mode = not self._wechat_utils.interface_test()

        if self._limited_mode:
            return return_msg
        else:
            self._wechat_utils.send_text(return_msg, wxid)
            return ""


    def handle_error(self, wxid: str, content: str, version: str, region: str, non_hashed_wxid: str="", e: BaseException=Exception()):
        traceback_info = traceback.format_exc()
        err_uuid = uuid.uuid1()
        logger.error(f"Error {err_uuid}: {e}\n{traceback_info}")

        if "incorrect header check" in str(e):
            return_msg = "你wahleak服务器又在胡言乱语力（\n要不再试试？"
        else:
            ErrorEMailSender(f"发生错误: {err_uuid}", f"{e}\n{traceback_info}").start()

            if wxid in cfg["wechat"]["wxid_admins"]:
                return_msg = "发生错误：{e}\n(错误识别码：{err_uuid})".format(e=e, err_uuid=err_uuid)
            else:
                return_msg = "发生错误，请联系管理员\n(错误识别码：{err_uuid})".format(err_uuid=err_uuid)

        return return_msg

    def handle_agreement(self, wxid: str, content: str, version: str, region: str, non_hashed_wxid: str=""):
        return agreement

    def handle_whitelist_join(self, wxid: str, content: str, version: str, region: str, non_hashed_wxid: str=""):
        my_preview = self.preview(wxid)
        if not my_preview:
            return_msg = "你还没有绑定，发送 “绑定 [你的UserID]” 绑定"
        else:
            if not my_preview["is_in_whitelist"]:
                return_msg = cfg["settings"]["whitelist"]["join_tips"]["not_exist"]
            else:
                return_msg = cfg["settings"]["whitelist"]["join_tips"]["exist"]

        return return_msg

    def handle_version(self, wxid: str, content: str, version: str, region: str, non_hashed_wxid: str=""):
        return_msg = "当前版本: {version}-{git} ({region})".format(version=version, region=region, git=maibox.git_sha)
        return return_msg

    def handle_help(self, wxid: str, content: str, version: str, region: str, non_hashed_wxid: str=""):
        return "帮助\n（若无特殊说明，中括号“[]”内文本为提示文本，请勿直接发送中括号）\n直接发送带有登入二维码的图片即可解析并绑定UserID\n发送 “绑定 [你的UserID或二维码内容]” 绑定UserID到微信\n发送 “润 [UserID]” 解小黑屋（已废弃）\n发送 “看我” 查看我的信息\n发送 “解绑” 解绑UserID\n发送 “解析 [二维码内容]” 解析UserID\n发送 “发票 [跑图票倍数2-6之间]” 进行发票（限时解禁）\n发送 “查票” 查询当前跑图票记录\n发送 “足迹” 查看当前出勤地区记录\n发送 “同步” 同步当前乐曲数据到水鱼查分器\n发送 “b50” 生成B50图片\n发送 “加入白名单” 以获取指引\n发送 “使用须知” 以查阅条款内容\n\n当前版本: {version}-{git} ({region})".format(version=version, region=region, git=maibox.git_sha)

    def handle_bind(self, wxid: str, content: str, version: str, region: str, non_hashed_wxid: str=""):
        split_content = self.final_word_cut(content)
        if len(split_content) == 2:
            if split_content[-1].isdigit():  # 如果是User ID
                resp = helpers.get_preview(int(split_content[-1]), self.dao)
                if resp["data"]["userId"] and resp["data"]["userName"]:
                    return_msg = "{userId}: {userName} ({playerRating})\n{result}\n温馨提示：当您取消关注公众号时您的账号绑定关系也会一并清除（不包含白名单记录）".format(
                        userId=resp["data"]["userId"],
                        userName=resp["data"]["userName"],
                        playerRating=resp["data"]["playerRating"],
                        result=self.bind(split_content[-1], wxid)
                    )
                else:
                    return_msg = "绑定失败，无法获取到该用户信息，请检查UserID是否正确"
            elif split_content[-1].startswith("SGWCMAID"):  # 如果是二维码
                result = self.getUserIDByQR(split_content[1])
                uid = result["userID"]
                eid = result["errorID"]
                if uid and eid == 0:
                    resp = helpers.get_preview(uid, self.dao)
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
    def handle_unbind(self, wxid: str, content: str, version: str, region: str, non_hashed_wxid: str=""):
        return self.unbind(wxid)

    def handle_logout(self, wxid: str, content: str, version: str, region: str, non_hashed_wxid: str=""):
        split_content = self.final_word_cut(content)
        if len(split_content) == 3:
            return_msg = helpers.logout(int(split_content[1]), int(split_content[2]))["msg"]
        else:
            blackroom = self.blackroom(wxid, int(split_content[1]))
            if blackroom:
                return_msg = blackroom
            else:
                return_msg = "未绑定或未指定UserID，发送 “绑定 [你的UserID]” 绑定或发送 “润 [UserID] [秒级Unix时间戳]” 解小黑屋"
        return return_msg

    def handle_preview(self, wxid: str, content: str, version: str, region: str, non_hashed_wxid: str=""):
        my_preview = self.detailed_preview(wxid, non_hashed_wxid)
        return_msg = ""
        if not my_preview:
            return_msg = "未绑定，发送 “绑定 [你的UserID]” 绑定"
        if isinstance(my_preview, str):
            return_msg = my_preview
        elif isinstance(my_preview, dict):
            last_game_data_character = get_version_label(int(my_preview["data"]["lastDataVersion"].split(".")[-1]))
            last_rom_ver_tuple = tuple(map(int, my_preview["data"]["lastRomVersion"].split(".")))
            last_data_ver_tuple = tuple(map(int, my_preview["data"]["lastDataVersion"].split(".")))

            return_msg = "{warning}微信用户ID（已哈希化）: {wxid}\n用户ID: {user_id}\n昵称: {user_name}\n游戏Rating: {player_rating}\n上次游戏版本：Ver.CN{rom_version}{data_char}\n封禁状态: {ban_state}\n\n请在微信“舞萌 | 中二”服务号上点击一次“玩家二维码”按钮以获取详细信息（无需再次发送二维码图片）".format(
                warning="警告！用户游戏版本异常\n" if (last_data_ver_tuple[0] != 1 and last_data_ver_tuple[1] % 5 != 0) or (last_rom_ver_tuple[0] != 1 and last_rom_ver_tuple[2] != 0) else "",
                wxid=wxid,
                user_id=my_preview["data"]["userId"],
                user_name=my_preview["data"]["userName"],
                player_rating=my_preview["data"]["playerRating"],
                rom_version=".".join(my_preview["data"]["lastRomVersion"].split(".")[0:2]),
                data_char="-{char}".format(char=last_game_data_character),
                ban_state=["正常", "警告", "封禁"][my_preview["data"]["banState"]],
                # login_status="正在上机" if my_preview["data"]["isLogin"] else "未上机",
                # whitelist_status="你当前是受邀用户\n" if my_preview["is_in_whitelist"] else ""
            ).strip()

            file_id = hashlib.md5(
                f"{wxid}_{int(time.time())}_{"".join(random.sample(string.ascii_letters + string.digits, 8))}".encode()).hexdigest().lower()
            filename = f"preview_{file_id}.png"

            user_data = {
              "nickname": my_preview["data"]["userName"],
              "rating": my_preview["data"]["playerRating"],
              "icon": my_preview["data"]["iconId"],
              "awake": my_preview["data"]["totalAwake"],
            }

            threading.Thread(target=call_user_img_preview, args=(filename, user_data, self._wechat_utils, non_hashed_wxid)).start()

            self._limited_mode = not self._wechat_utils.interface_test()
            if self._limited_mode:
                return_msg += "\n\n用户预览图片获取地址：\n{api_url}/img/preview?id={file_id}\n图片文件随时可能会被删除，还请尽快下载".format(
                    api_url=cfg["urls"]["api_url"], file_id=file_id)
            else:
                return_msg += "\n\n稍后发送用户预览图片"

        return return_msg

    def handle_resolve(self, wxid: str, content: str, version: str, region: str, non_hashed_wxid: str=""):
        split_content = self.final_word_cut(content)
        if len(split_content) != 2:
            return_msg = "发送 “解析 [二维码内容]” 解析UserID"
        else:
            result = self.getUserIDByQR(split_content[1])
            uid = result["userID"]
            eid = result["errorID"]
            if uid and eid == 0:
                return_msg = "解析成功，UserID: {uid}\n请发送 “绑定 {uid}” 以绑定该UserID".format(uid=uid)
            else:
                return_msg = "解析失败，请检查二维码是否正确"
        return return_msg

    def handle_send_ticket(self, wxid: str, content: str, version: str, region: str, non_hashed_wxid: str=""):
        split_content = self.final_word_cut(content)
        if len(split_content) != 2:
            return_msg = "发送 “发券 [倍数]” 发送倍券"
        else:
            user_id = self.dao.getUid(wxid)
            if not user_id:
                return_msg = "未绑定，发送 “绑定 [你的UserID]” 绑定"
            else:
                my_preview = self.preview(wxid)
                if isinstance(my_preview, dict):
                    if True or my_preview["is_in_whitelist"]:
                        if split_content[1].isdigit() and 6 >= int(split_content[1]) >= 2:
                            return_msg = helpers.send_ticket(user_id, int(split_content[1]))["msg"]
                        else:
                            return_msg = "倍数不在2-6之间"
                    else:
                        return_msg = "你没有权限，发送 “加入白名单” 以获取指引"
                else:
                    return_msg = my_preview

        return return_msg

    def handle_query_ticket(self, wxid: str, content: str, version: str, region: str, non_hashed_wxid: str=""):
        uid = self.dao.getUid(wxid)
        data = helpers.query_ticket(uid)
        message = "用户ID: {userId}\n倍券类型数量: {length}\n倍券列表:\n".format(
            userId=data["data"]["userId"],
            length=data["data"]["length"]
        )
        for i in range(len(data["data"]["userChargeList"])):
            message += "{order}. 倍券ID：{chargeId}\n当前持有{stock}张，最近一次购买于{purchaseDate}，有效期至{validDate}\n".format(
                order=i + 1,
                chargeId=data["data"]["userChargeList"][i]["chargeId"],
                stock=data["data"]["userChargeList"][i]["stock"],
                purchaseDate=data["data"]["userChargeList"][i]["purchaseDate"],
                validDate=data["data"]["userChargeList"][i]["validDate"]
            )
        return_msg = message
        return return_msg

    def handle_sync(self, wxid: str, content: str, version: str, region: str, non_hashed_wxid: str=""):
        split_content = self.final_word_cut(content)
        return_msg = ""
        flag = False
        uid = self.dao.getUid(wxid)
        if not uid:
            return_msg = "未绑定，发送 “绑定 [你的UserID]” 绑定"
            return return_msg
        username, password = self.dao.get_df_account(wxid)
        if username and password:
            return_msg += "水鱼账户: {username}\n".format(username=username)
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

    def handle_b50(self, wxid: str, content: str, version: str, region: str, non_hashed_wxid: str=""):
        return self.b50(wxid, non_hashed_wxid)

    def handle_region(self, wxid: str, content: str, version: str, region: str, non_hashed_wxid: str=""):
        return self.region(wxid)

    def handle_ai(self, wxid: str, content: str, version: str, region: str, non_hashed_wxid: str=""):
        return ai_chat(content.strip(), wxid)

    def handle_admin(self, wxid: str, content: str, version: str, region: str, non_hashed_wxid: str=""):
        split_content = self.final_word_cut(content)
        return_msg = ""
        if wxid not in cfg["wechat"]["wxid_admins"]:
            return_msg = ai_chat(content.strip(), wxid)
        else:
            if len(split_content) > 1 and split_content[1] in self.admin_command_map:
                return_msg = self.admin_command_map[split_content[1]](content)
            else:
                return_msg = "行为未定义"

        return return_msg

    def handle_admin_log(self, content: str):
        if not cfg["email"]["enable"]:
            return "邮箱模块未启用"
        ErrorEMailSender("实时日志", "").start()
        return "日志将在稍后发送"

    def handle_admin_whitelist(self, content: str):
        split_content = self.final_word_cut(content)
        return_msg = ""
        if len(split_content) == 2:
            whitelist = self.dao.getAllWhitelist()
            if whitelist:
                return_msg = "\n".join(whitelist)
                return_msg += "\nlength: {}".format(len(whitelist))
            else:
                return_msg = "白名单为空"
        elif split_content[2] == "add":
            resp = helpers.get_preview(int(split_content[-1]), self.dao)
            if resp["data"]["userId"] and resp["data"]["userName"]:
                return_msg = "{userId}: {userName} ({playerRating})\n".format(
                    userId=resp["data"]["userId"],
                    userName=resp["data"]["userName"],
                    playerRating=resp["data"]["playerRating"]
                )
                if self.dao.addWhitelist(int(split_content[3])):
                    return_msg += "添加成功"
                else:
                    return_msg += "添加失败"
        elif split_content[2] == "remove":
            resp = helpers.get_preview(int(split_content[-1]), self.dao)
            if resp["data"]["userId"] and resp["data"]["userName"]:
                return_msg = "{userId}: {userName} ({playerRating})\n".format(
                    userId=resp["data"]["userId"],
                    userName=resp["data"]["userName"],
                    playerRating=resp["data"]["playerRating"]
                )
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
            return "绑定成功，如需解绑，发送 “解绑” 以解绑"
        else:
            return "绑定失败，您已经绑定过UserID，如需解绑，发送 “解绑” 以解绑"

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
                return helpers.logout(uid, timestamp)["msg"]
            except Exception as e:
                logger.error(f"Error {uuid.uuid1()}: {e}")
                logger.error(f"{traceback.format_exc()}")
                return "访问失败，可能是服务器错误"
        else:
            return None

    def preview(self,wxid):
        uid = self.dao.getUid(wxid)
        if uid:
            try:
                return helpers.get_preview(uid, self.dao)
            except Exception as e:
                logger.error(f"Error {uuid.uuid1()}: {e}")
                logger.error(f"{traceback.format_exc()}")
                return "访问失败，可能是服务器错误"
        else:
            return None

    def detailed_preview(self,wxid,openid=""):
        uid = self.dao.getUid(wxid)
        template = """{warning}
微信用户ID（已哈希化）: {wxid}
用户ID: {user_id}
昵称: {user_name}
游戏Rating: {player_rating}
上次游戏版本：Ver.CN{rom_version}{data_char}
封禁状态: {ban_state}
头像：{icon_name}
姓名框：{plate_name}
称号：{title_name}
背景：{frame_name}
搭档：{partner_name}
旅行伙伴: {charater_str}
旅行伙伴等级: {charater_level_str}
旅行伙伴觉醒: {charater_awakening_str}
最后一次登录时间：{last_login_date}
入坑天数：{play_day_count}天（{first_play_date}）
入坑版本：Ver.CN{first_rom_version}{first_data_char}
累计游玩次数：{play_count}
当前版本游玩次数：{current_play_count}"""
        if uid:
            try:
                data = helpers.get_preview_detailed(uid)
                if data["msg"]:
                    if not data["is_got_qr_code"]:
                        return self.preview(wxid)
                    return data["msg"]
                last_game_data_character = get_version_label(int(data["data"]["lastDataVersion"].split(".")[-1]))
                last_rom_ver_tuple = tuple(map(int, data["data"]["lastRomVersion"].split(".")))
                last_data_ver_tuple = tuple(map(int, data["data"]["lastDataVersion"].split(".")))

                first_game_data_character = get_version_label(int(data["data"]["firstDataVersion"].split(".")[-1]))
                first_rom_ver_tuple = tuple(map(int, data["data"]["firstRomVersion"].split(".")))
                first_data_ver_tuple = tuple(map(int, data["data"]["firstDataVersion"].split(".")))

                text = template.format(
                    warning="警告！用户游戏版本异常\n" if (last_data_ver_tuple[0] != 1 and last_data_ver_tuple[
                        1] % 5 != 0) or (last_rom_ver_tuple[0] != 1 and last_rom_ver_tuple[2] != 0) else "",
                    wxid=wxid,
                    user_id=data["user_id"],
                    user_name=data["data"]["userName"],
                    player_rating=data["data"]["playerRating"],
                    rom_version=".".join(data["data"]["lastRomVersion"].split(".")[0:2]),
                    data_char="-{char}".format(char=last_game_data_character),
                    ban_state=["正常", "警告", "封禁"][data["data"]["banState"]],
                    icon_name=data["data"]["iconName"],
                    plate_name=data["data"]["plateName"],
                    title_name=data["data"]["titleName"],
                    frame_name=data["data"]["frameName"],
                    partner_name=data["data"]["partnerName"],
                    charater_str=" ".join(data["data"]["charaName"]),
                    charater_level_str=" ".join(map(str, data["data"]["charaLevel"])),
                    charater_awakening_str=" ".join(map(str, data["data"]["charaAwakening"])),
                    last_login_date=data["data"]["lastLoginDate"],
                    play_day_count=(datetime.datetime.now() - datetime.datetime.strptime(data["data"]["firstPlayDate"], "%Y-%m-%d %H:%M:%S")).days,
                    first_play_date=data["data"]["firstPlayDate"],
                    first_rom_version=".".join(data["data"]["firstRomVersion"].split(".")[0:2]),
                    first_data_char="-{char}".format(char=first_game_data_character),
                    play_count=data["data"]["playCount"],
                    current_play_count=data["data"]["currentPlayCount"]
                ).strip()

                file_id = hashlib.md5(
                    f"{wxid}_{int(time.time())}_{"".join(random.sample(string.ascii_letters + string.digits, 8))}".encode()).hexdigest().lower()
                filename = f"user_{file_id}.png"

                user_data = {
                    "nickname": data["data"]["userName"],
                    "title": data["data"]["titleName"],
                    "icon": data["data"]["iconId"],
                    "frame": data["data"]["frameId"],
                    "plate": data["data"]["plateId"],
                    "rating": data["data"]["playerRating"],
                    "classRank": data["data"]["classRank"],
                    "courseRank": data["data"]["courseRank"],
                    "titleRare": data["data"]["titleRare"],
                    "version": "Ver.CN{rom_version}{data_char}".format(
                        rom_version=".".join(data["data"]["lastRomVersion"].split(".")[0:2]),
                        data_char="-{char}".format(char=last_game_data_character)
                    )
                }
                threading.Thread(target=call_user_img, args=(filename, user_data, self._wechat_utils, openid)).start()

                self._limited_mode = not self._wechat_utils.interface_test()
                if self._limited_mode:
                    text += "\n\n用户预览图片获取地址：\n{api_url}/img/user?id={file_id}\n图片文件随时可能会被删除，还请尽快下载".format(
                        api_url=cfg["urls"]["api_url"], file_id=file_id)
                else:
                    text += "\n\n稍后发送用户预览图片"

                return text

            except Exception as e:
                logger.error(f"Error {uuid.uuid1()}: {e}")
                logger.error(f"{traceback.format_exc()}")
                return "访问失败，可能是服务器错误"
        else:
            return None

    def region(self,wxid):
        uid = self.dao.getUid(wxid)
        if uid:
            try:
                user_region = helpers.get_user_region(uid)["data"]
                text = "你目前一共在{length}个地区出过勤: \n".format(length=user_region["length"])
                for i in range(len(user_region["userRegionList"])):
                    text += "\n{order}. 在 {regionName} 勤过{playCount}次\n首次记录于{created}".format(
                        order=i+1,
                        regionName=user_region["userRegionList"][i]['regionName'],
                        playCount=user_region["userRegionList"][i]['playCount'],
                        created=user_region["userRegionList"][i]['created']
                    )
                return text
            except Exception as e:
                logger.error(f"Error {uuid.uuid1()}: {e}")
                logger.error(f"{traceback.format_exc()}")
                return "访问失败，可能是服务器错误"
        else:
            return None

    def getUserIDByQR(self, qr_code):
        if (len(qr_code) == 84) and qr_code.startswith("SGWCMAID") and qr_code[8:20].isdigit() and bool(re.match(r'^[0-9A-F]+$', qr_code[20:])):
            return helpers.get_user_id_by_qr(qr_code)
        else:
            return None

    def b50(self, wxid, non_hashed_wxid=""):
        return_msg = ""
        username, password = self.dao.get_df_account(wxid)
        uid = self.dao.getUid(wxid)
        preview = helpers.get_preview(uid, self.dao)
        nickname = preview["data"]["userName"]
        icon_id = preview["data"]["iconId"]
        if username and password:
            return_msg += "水鱼账户: {username}\n".format(username=username)
            if fish_sync.update_fish(username, password, uid):
                return_msg += "水鱼同步成功\n"
            else:
                return_msg += "水鱼同步失败，请检查用户名和密码是否正确"
        else:
            return_msg += "未绑定水鱼账户，发送“同步 [用户名] [密码]”以绑定水鱼账户\n"
            return return_msg
        file_id = hashlib.md5(
            f"{wxid}_{int(time.time())}_{"".join(random.sample(string.ascii_letters + string.digits, 8))}".encode()).hexdigest().lower()
        filename = f"b50_{file_id}.png"

        threading.Thread(target=call_b50, args=(username, filename, nickname, icon_id, self._wechat_utils, non_hashed_wxid,)).start()
        self._limited_mode = not self._wechat_utils.interface_test()
        if self._limited_mode:
            return_msg += "\nb50图片获取地址：\n{api_url}/img/b50?id={file_id}\n图片文件随时可能会被删除，还请尽快下载".format(api_url=cfg["urls"]["api_url"], file_id=file_id)
        else:
            return_msg += "\n稍后发送b50图片"
        return return_msg.strip()
