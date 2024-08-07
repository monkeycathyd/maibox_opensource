import requests

from maibox.orm import Dao

import json
import requests
from requests.exceptions import RequestException

class ProberAPIClient:
    def __init__(self):
        self.username = ""
        self.password = ""
        self.network_timeout = 10
        self.client = requests.Session()
        self.jwt = ""

    def login(self):
        body = {"username": self.username, "password": self.password}

        try:
            response = self.client.post(
                "https://www.diving-fish.com/api/maimaidxprober/login",
                headers={"Content-Type": "application/json"},
                json=body,
                timeout=self.network_timeout,
            )
        except RequestException as e:
            raise RuntimeError("登录失败: {}".format(e))

        if response.status_code != 200:
            raise ValueError("登录凭据错误")

        print("登录成功")
        self.jwt = response.cookies.get("jwt_token", "")    # 提取jwt_token
        self.client.cookies.set("jwt_token", self.jwt)  # 附加jwt_token

    def get_player_token(self, username, password):
        if not self.jwt:
            self.username = username
            self.password = password
            self.login()

        url = "https://www.diving-fish.com/api/maimaidxprober/player/profile"

        try:
            response = self.client.get(url)
            response.raise_for_status()  # 检查响应状态码
        except RequestException as e:
            try:    # 检查返回信息中是否包含具体错误信息
                message = response.json().get("message", "Unknown error")
            except Exception:
                message = "Unknown error"
            raise RuntimeError(f"GET 请求失败: {e}, message: {message}")

        return response.json()["import_token"]  # json已转换为python字典


dao = Dao()

df_all = dao.get_all_df_accounts()
for df in df_all:
    try:
        print(df)
        client = ProberAPIClient()
        token = client.get_player_token(df[1], df[2])
        if len(token) > 0:
            dao.bind_df_token(df[0], token)
    except:
        pass
