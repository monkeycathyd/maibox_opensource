# 导入必要的模块和包，用于实现应用程序的功能
import os
import platform
import re
import traceback
import uuid
import json
import time
from datetime import datetime

import urllib3
import xmltodict

import maibox.config as config
from flask import Flask, request, redirect, Response, send_file
from flask_cors import CORS

from maibox import chime
from maibox.SocketHttps import HttpClient
from maibox.process_threads import ErrorEMailSender
from maibox.text_chat_handler import TextChatHandler
from maibox.auto_bot import logout, send_ticket, dump_user_all, get_preview, query_ticket
from maibox.orm import Dao
from maibox.music_record_generate import render_html
from maibox.utils import getLogger, check_wx_auth

server_url = "https://maimai-gm.wahlap.com:42081/Maimai2Servlet/"
server = urllib3.util.parse_url(server_url)

# 初始化日志记录器和Flask应用实例
logger = getLogger(__name__)
app = Flask(__name__)
CORS(app)

# 加载服务器配置，并创建数据库访问对象
server_config = config.get_config()
dao = Dao()

# 初始化文本聊天处理器
wechat_handler = TextChatHandler(dao)

# 定义认证装饰器，用于检查用户是否在白名单中
def auth(func):
    def wrapper(*args, **kwargs):
        uid = list(map(int, request.args.get('uid').split("pp")))
        if server_config["settings"]["whitelist"]["enable"]:
            if not dao.isWhitelist(uid[0]):
                return {"is_disallowed": True}
        return func(*args, **kwargs)
    return wrapper

# 在每个请求之前记录请求信息
@app.before_request
def log_request():
    logger.info(f"Request: {request.method} {request.path} {request.content_length} {request.headers} {request.data}")

# 在每个请求之后记录响应信息
@app.after_request
def process_response(response: Response):
    logger.info(f"Response: {response.status_code} {response.content_length} {response.headers}")
    return response

# 处理异常，记录错误并发送错误邮件
@app.errorhandler(Exception)
def error_handler(e):
    traceback_info = traceback.format_exc()
    err_uuid = uuid.uuid4()
    logger.error(f"Error {err_uuid}:{e}\n{traceback_info}")
    if "incorrect header check" not in str(e):
        ErrorEMailSender(f"发生错误: {err_uuid}", f"{e}\n{traceback_info}").start()

# 应用的路由和处理函数，实现不同的API接口
@app.route('/')
def index():
    return redirect(server_config["main_url"])

@app.route('/img/b50')
def img_b50():
    file_id = request.args.get('id', "")
    if not re.match(r'^[0-9a-z]+$', file_id):
        return """<meta name="viewport" content="width=device-width,initial-scale=1.0,user-scalable=yes"/><h1 style='text-align: center;color: red;'>文件ID错误</h1>""", 404
    filename = f"b50_{file_id}.jpg"
    filepath = os.path.join(os.getcwd(), "img", filename)
    if os.path.exists(filepath):
        return send_file(filepath)
    elif os.path.exists(os.path.join(os.getcwd(), "img", f"{filename}.flag")):
        return """<meta name="viewport" content="width=device-width,initial-scale=1.0,user-scalable=yes"/><h1 style='text-align: center;color: red;'>图片正在生成，请稍后</h1><script>setTimeout(()=>{location.reload()}, 1500)</script>""", 404
    else:
        return """<meta name="viewport" content="width=device-width,initial-scale=1.0,user-scalable=yes"/><h1 style='text-align: center;color: red;'>文件id错误</h1>""", 404

@app.route('/Maimai2Servlet/<api>', methods=['POST'], endpoint='proxy')
def proxy(api):
    header = {
        "Content-Type": "application/json",
        "User-Agent": request.headers.get("User-Agent"),
        "charset": request.headers.get("charset", "UTF-8"),
        "Mai-Encoding":request.headers.get("Mai-Encoding"),
        "Content-Encoding": "deflate",
        "Content-Length": request.content_length,
        "Host": server.host,
    }
    resp = HttpClient.post(urllib3.util.parse_url(server_url + api), header, request.data)
    response = Response(resp["body"], mimetype="application/json")
    response.status_code = int(resp["status_code"])
    for key, value in resp["headers"].items():
        response.headers[key] = value
    return response

@app.route('/api/qr', methods=['GET'], endpoint='qr')
def qr():
    if platform.system() != "Windows":
        return {
            "userID": 0,
            "errorID": 88,
            "timestamp": datetime.now().strftime("%Y%m%d%H%M%S")[2:]
        }
    content = request.args.get('content')
    if not(content.startswith("SGWCMAID") and len(content) == 84 and bool(re.match(r'^[0-9A-F]+$', content[20:]))):
        return {
            "userID": 0,
            "errorID": 99,
            "timestamp": datetime.now().strftime("%Y%m%d%H%M%S")[2:],
        }
    getUserData = chime.GetUserData('MAID', 'A63E-01E11910000', '', content[20:])
    while not getUserData.is_end():
        getUserData.execute()
    return {
        "userID": getUserData.get_user_id(),
        "errorID": getUserData.get_error_id(),
        "timestamp": datetime.now().strftime("%Y%m%d%H%M%S")[2:],
    }

@app.route('/api/logout', endpoint='logout')
def logout_app():
    uid = list(map(int, request.args.get('uid').split("pp")))[-1]
    return logout(uid)

@app.route('/api/ticket', endpoint='ticket')
@auth
def ticket_app():
    ticket_id = int(request.args.get('ticket_id'))
    uid = list(map(int, request.args.get('uid').split("pp")))
    return send_ticket(uid[-1], ticket_id)

@app.route('/api/dump', endpoint='dump')
def dump_app():
    uid = list(map(int, request.args.get('uid').split("pp")))
    return dump_user_all(uid[-1])

@app.route('/api/get_ticket', endpoint='get_ticket')
def get_ticket_app():
    uid = list(map(int, request.args.get('uid').split("pp")))
    return query_ticket(uid[-1])

@app.route('/api/preview', endpoint='preview')
def preview_app():
    uid = list(map(int, request.args.get('uid').split("pp")))[-1]
    return get_preview(uid, dao)

@app.route('/api/frontend_config')
def frontend_config():
    return {
        "frontend_setting": config.get_config_with_reload()["settings"]["frontend_setting"],
        "release_info": {
            "version": request.headers.get("X-Cloudbase-Version", "unknown"),
        },
        "support_mai_version": list(map(int, server_config["arcade_info"]["data_version"].split("."))),
        "time_avg": ""
    }

@app.route('/api/get_user_music_record', endpoint='get_user_music_record')
def get_user_music_record():
    uid = int(request.args.get('uid'))
    resp = Response(render_html(uid), mimetype='application/octet-stream')
    resp.headers['Content-Disposition'] = f'attachment; filename="music_exported_{uid}_{int(time.time())}.html"'
    return resp

@app.route('/api/wechat', methods=['POST', 'GET'], endpoint='wechat')
def wechat():
    # 使用微信云托管方式接入微信公众号
    version = request.headers.get("X-Cloudbase-Version", "unknown")
    region = request.headers.get("X-Wx-Region", "unknown")
    if request.headers.get("X-Wx-Appid", "") != server_config["wechat"]["app_id"]:
        return "error", 403
    if request.method == 'POST':
        data = request.json
        logger.info(data)
        if "action" in data:
            return "success"
        else:
            msg = ""
            if data["MsgType"] == "event":
                msg = wechat_handler.process_event(data["Event"], data["FromUserName"], version, region)
            elif data["MsgType"] == "image":
                msg = wechat_handler.process_img(data["PicUrl"], data["FromUserName"])
            elif data["MsgType"] == "text":
                msg = wechat_handler.process_chat(data["Content"], data["FromUserName"], version, region)
            return json.dumps({
                "FromUserName":data["ToUserName"],
                "ToUserName":data["FromUserName"],
                "CreateTime":int(time.time()),
                "MsgType":"text",
                "Content":msg
            }, ensure_ascii=False)
    else:
        return "success"

@app.route('/api/wechat/native', methods=['GET', 'POST'])
def wechat_native():
    # 使用传统方式接入微信公众号
    version = region = "native_mode"
    signature = request.args.get('signature')
    timestamp = request.args.get('timestamp')
    nonce = request.args.get('nonce')
    if not check_wx_auth(signature, timestamp, nonce):
        return ""
    if request.method == "GET":
        # 表示是第一次接入微信服务器的验证
        return request.args.get('echostr')
    elif request.method == "POST":
        # 表示微信服务器转发消息过来
        xml_str = request.data
        if not xml_str:
            return ""
        # 对xml字符串进行解析
        data = xmltodict.parse(xml_str)["xml"]
        msg = ""
        if data["MsgType"] == "event":
            msg = wechat_handler.process_event(data["Event"], data["FromUserName"], version, region)
        elif data["MsgType"] == "image":
            msg = wechat_handler.process_img(data["PicUrl"], data["FromUserName"])
        elif data["MsgType"] == "text":
            msg = wechat_handler.process_chat(data["Content"], data["FromUserName"], version, region)
        return xmltodict.unparse({
            "xml":{
                "FromUserName": data["ToUserName"],
                "ToUserName": data["FromUserName"],
                "CreateTime": int(time.time()),
                "MsgType": "text",
                "Content": msg
            }
        })

