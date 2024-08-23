import json
import random
import traceback

from openai import OpenAI
from tencentcloud.common import credential
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.hunyuan.v20230901 import hunyuan_client, models

from maibox.manager.config import get_config
from maibox.util.utils import getLogger

logger = getLogger(__name__)
cfg = get_config()
providers_weights = {
    "tencent": 0,
    "alibaba": 1
}
setting_prompt = cfg["ai"]["setting_prompt"]

tencent_cred = None
if cfg["ai"]["tencent_api"]["secret_id"] and cfg["ai"]["tencent_api"]["secret_key"]:
    logger.info("Tencent AI enabled")
    tencent_cred = credential.Credential(cfg["ai"]["tencent_api"]["secret_id"], cfg["ai"]["tencent_api"]["secret_key"])

ali_client = None
if cfg["ai"]["ali_ai_key"]:
    logger.info("Aliyun AI enabled")
    ali_client = OpenAI(
        api_key=cfg["ai"]["ali_ai_key"],
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    )

user_prompt_records = {}

class AIProviders:
    @staticmethod
    def ai_chat_tencent(prompts):
        logger.info("Tencent AI: " + str(prompts))
        if not tencent_cred:
            logger.warning("Tencent AI secret id and secret key not set")
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
                "Messages": [{
                    "Role": prompt["role"],
                    "Content": prompt["content"]
                } for prompt in ([
                  {'role': 'system', 'content': setting_prompt},
              ] + prompts)]
            }
            req.from_json_string(json.dumps(params))
            resp = client.ChatCompletions(req)
            return json.loads(resp.to_json_string())["Choices"][0]["Message"]["Content"]
        except TencentCloudSDKException as err:
            return "抱歉，我暂时无法回答这个问题"

    @staticmethod
    def ai_chat_alibaba(prompts):
        logger.info("Aliyun AI: " + str(prompts))
        if not ali_client:
            logger.warning("Aliyun AI key not set")
            return "抱歉，我暂时无法回答这个问题"
        completion = ali_client.chat.completions.create(
            model="qwen-turbo",
            messages=([
                         {'role': 'system', 'content': setting_prompt},
                     ] + prompts),
            temperature=0.8,
            top_p=0.8
        )
        return json.loads(completion.model_dump_json())["choices"][0]["message"]["content"]


def ai_chat(prompt, user_id="1234"):
    logger.info("User: " + prompt)
    if not cfg["ai"]["enable"]:
        logger.info("AI disabled")
        return "抱歉，我暂时无法回答这个问题"
    try:
        provider = random.choices(list(providers_weights.keys()), weights=list(providers_weights.values()), k=1)[0]
        if user_id not in user_prompt_records:
            user_prompt_records[user_id] = []
        logger.info(f"Using {provider.upper()} AI")
        logger.info(f"Prompt from {user_id}: {provider}")
        user_prompt_records[user_id].append({
            "role": "user",
            "content": prompt
        })
        resp = getattr(AIProviders, "ai_chat_" + provider)(user_prompt_records[user_id])
        user_prompt_records[user_id].append({
            "role": "assistant",
            "content": resp
        })
        if len(user_prompt_records[user_id]) > 20:
            user_prompt_records[user_id] = user_prompt_records[user_id][-20:]
        return f"{resp}\n\n大模型供应商: {provider}\n文本内容由AI大模型生成，公众号不对该内容负责"
    except Exception as e:
        logger.error(f"AI error: {e}")
        logger.error(f"{traceback.format_exc()}")
        return "抱歉，我暂时无法回答这个问题"
