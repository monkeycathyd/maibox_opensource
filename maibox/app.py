# 导入必要的模块和包，用于实现应用程序的功能
import os
import re
import traceback
import uuid
import json
import logging
import time

import maibox.config as config
from flask import Flask, request, redirect, Response, send_file
from flask_cors import CORS

from maibox.automate import ErrorEMailSender
from maibox.text_chat_handler import TextChatHandler
from maibox.auto_bot import logout, send_ticket, dump_user_all, get_preview, query_ticket
from maibox.orm import Dao
from maibox.music_record_generate import render_html
from maibox.utils import getLogger

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
        if server_config["whitelist_enabled"]:
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
        "frontend_setting": config.get_config_with_reload()["frontend_setting"],
        "release_info": {
            "version": request.headers.get("X-Cloudbase-Version", "unknown"),
        },
        "support_mai_version": list(map(int, server_config["data_version"].split("."))),
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
    version = request.headers.get("X-Cloudbase-Version", "unknown")
    region = request.headers.get("X-Wx-Region", "unknown")
    if request.headers.get("X-Wx-Appid", "") != server_config["wechat_app_id"]:
        return "error", 403
    if request.method == 'POST':
        data = request.json
        logger.info(data)
        if "action" in data:
            return "success"
        else:
            if data["MsgType"] == "event":
                msg = wechat_handler.process_event(data["Event"], data["FromUserName"], version, region)
            elif data["MsgType"] == "image":
                msg = wechat_handler.process_img(data["PicUrl"], data["FromUserName"])
            else:
                msg = wechat_handler.process_chat(data["Content"], data["FromUserName"], version, region)
            data = {
                "FromUserName":data["ToUserName"],
                "ToUserName":data["FromUserName"],
                "CreateTime":int(time.time()),
                "MsgType":"text",
                "Content":msg
            }
            return json.dumps(data, ensure_ascii=False)
    else:
        return "success"

@app.route('/img/b50')
def img_b50():
    file_id = request.args.get('id', "")
    if not re.match(r'^[0-9a-z]+$', file_id):
        return """<meta name="viewport" content="width=device-width,initial-scale=1.0,user-scalable=yes"/><h1 style='text-align: center;color: red;'>文件id错误</h1>""", 404
    filename = f"b50_{file_id}.jpg"

    if os.path.exists(f"img/{filename}"):
        return send_file(f"../img/{filename}")
    elif os.path.exists(f"img/{filename}.flag"):
        return """<meta name="viewport" content="width=device-width,initial-scale=1.0,user-scalable=yes"/><h1 style='text-align: center;color: red;'>图片正在生成，请稍后</h1><script>setTimeout(()=>{location.reload()}, 500)</script>""", 404
    else:
        return """<meta name="viewport" content="width=device-width,initial-scale=1.0,user-scalable=yes"/><h1 style='text-align: center;color: red;'>文件id错误</h1>""", 404
