import requests
import re

from maibox import music_record_generate as music
from maibox.utils import getLogger

logger = getLogger(__name__)


def update_fish(token, userid):
    resp = requests.post(
        url='https://www.diving-fish.com/api/pageparser/page',
        headers={
            'Content-Type': 'text/plain',
            "Import-Token": token
        },
        json=music.get_user_music_details_df(userid)
    )

    logger.info(resp.text)
    return resp.status_code == 200