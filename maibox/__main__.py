import os
import sys

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
    host = server_config["server"]["host"]
    port = server_config["server"]["port"]
    server = pywsgi.WSGIServer((host, port), app)
    logger.info(f"Server running at http://{host}:{port}")
    server.serve_forever()
    logger.info('Server stopped')
except KeyboardInterrupt:
    server.stop()
    logger.info('Server stopped')
    os._exit(0)
except:
    logger.info("Error:", sys.exc_info()[0])
    os._exit(-1)
