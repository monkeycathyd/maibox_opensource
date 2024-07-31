import json
import random

from openai import OpenAI
from tencentcloud.common import credential
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.hunyuan.v20230901 import hunyuan_client, models

from maibox.config import get_config


cfg = get_config()
providers_weights = {
    "tencent": 0,
    "alibaba": 1
}
setting_prompt = cfg["ai"]["setting_prompt"]

tencent_cred = None
if cfg["ai"]["tencent_api"]["secret_id"] and cfg["ai"]["tencent_api"]["secret_key"]:
    tencent_cred = credential.Credential(cfg["ai"]["tencent_api"]["secret_id"], cfg["ai"]["tencent_api"]["secret_key"])

ali_key = None
if cfg["ai"]["ali_ai_key"]:
    ali_key = cfg["ai"]["ali_ai_key"]

class AIProviders:
    @staticmethod
    def ai_chat_tencent(prompt):
        if not tencent_cred:
            return "抱歉，我暂时无法回答这个问题"
        try:
            httpProfile = HttpProfile()
            httpProfile.endpoint = "hunyuan.tencentcloudapi.com"

            clientProfile = ClientProfile()
            clientProfile.httpProfile = httpProfile
            client = hunyuan_client.HunyuanClient(tencent_cred, "ap-beijing", clientProfile)

            req = models.ChatCompletionsRequest()
            params = {
                "Model": "hunyuan-lite",
                "Messages": [
                    {
                        "Role": "system",
                        "Content": setting_prompt
                    },
                    {
                        "Role": "user",
                        "Content": prompt
                    }
                ]
            }
            req.from_json_string(json.dumps(params))
            resp = client.ChatCompletions(req)
            return json.loads(str(resp))["Choices"][0]["Message"]["Content"]
        except TencentCloudSDKException as err:
            raise err

    @staticmethod
    def ai_chat_alibaba(prompt):
        if not ali_key:
            return "抱歉，我暂时无法回答这个问题"
        client = OpenAI(
            api_key=ali_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )

        completion = client.chat.completions.create(
            model="qwen-turbo",
            messages=[
                {'role': 'system', 'content': setting_prompt},
                {'role': 'user', 'content': prompt}
            ],
            temperature=0.8,
            top_p=0.8
        )
        return json.loads(completion.model_dump_json())["choices"][0]["message"]["content"]


def ai_chat(prompt):
    if not cfg["ai"]["enable"]:
        return "抱歉，我暂时无法回答这个问题"
    try:
        provider = random.choices(list(providers_weights.keys()), weights=list(providers_weights.values()), k=1)[0]
        resp = getattr(AIProviders, "ai_chat_" + provider)
        return f"{resp(prompt)}\n\n大模型供应商: {provider}\n文本内容由AI大模型生成，公众号不对该内容负责"
    except:
        return "抱歉，我暂时无法回答这个问题"
