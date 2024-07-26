import requests
import re

from maibox import music_record_generate as music
from maibox.utils import getLogger

logger = getLogger(__name__)

def compose_post_form(username, password, content):
    return f"<login><u>{username}</u><p>{password}</p></login>" + re.search(r'<html.*?>(.*?)</html>', content, re.DOTALL).group(1).replace('\n', ' ').strip()


def update_fish(username, password, userid):
    details = music.render_html(userid)
    resp = requests.post(
        url='https://www.diving-fish.com/api/pageparser/page',
        headers={
            'Content-Type': 'text/plain'
        },
        data=compose_post_form(username, password, details)
    )

    logger.info(resp.text)
    return resp.status_code == 200