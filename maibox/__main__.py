import os
import platform
import sys
import time

import maibox.config as config
from gevent import pywsgi

from maibox.app import app
from maibox.utils import getLogger

server_config = config.get_config()

logger = getLogger(__name__)

try:
    logger.info(f"Running at {os.getcwd()}")
    if not os.path.exists("./img"):
        os.mkdir("./img")
    if platform.system() != "Windows" and (not server_config["settings"]["skip_chime_warning"]):
        for i in range(3):
            logger.warning("!!!!!WARNING!!!!! Local chime resolving service is not available on non-Windows system !!!!!WARNING!!!!!")
            logger.warning("!!!!!警告!!!!! 本地解析Chime二维码服务在非Windows平台上不可用 !!!!!警告!!!!!")
            time.sleep(0.5)
    logger.info("Starting server...")
    host = server_config["server"]["host"]
    port = server_config["server"]["port"]
    server = pywsgi.WSGIServer((host, port), app)
    logger.info(f"Server running on http://{host}:{port}")
    server.serve_forever()
    logger.info('Server stopped')
except KeyboardInterrupt:
    server.stop()
    logger.info('Server stopped')
    os._exit(0)
except:
    logger.info("Error:", sys.exc_info()[0])
    os._exit(-1)
