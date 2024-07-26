import ssl
import http.client

import urllib3.util

# 创建一个SSL上下文，忽略证书验证
context = ssl.create_default_context()
context.check_hostname = False
context.verify_mode = ssl.CERT_NONE

class HttpClient:
    @staticmethod
    def post(url: urllib3.util.Url, headers, body, timeout: float = 3):
        conn = http.client.HTTPSConnection(host=url.host, port=url.port, context=context, timeout=timeout)

        headers["Content-Length"] = str(len(body))
        headers["Host"] = url.host

        # 发送POST请求
        conn.request("POST", url.path, body, headers)

        # 获取响应
        response = conn.getresponse()
        response_data = response.read()

        # 解析响应头
        response_headers = dict(response.getheaders())

        return {
            "status_code": response.status,
            "headers": response_headers,
            "body": response_data
        }
