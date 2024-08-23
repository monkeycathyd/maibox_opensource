import threading

from maibox.manager.orm import Dao


class UserMsgRecorder:
    def __init__(self, dao: Dao):
        self.dao = dao

    def add(self, wxid: str, msg: str, msg_type: str, is_response: bool=False):
        threading.Thread(target=self.dao.add_record, args=(wxid, msg, msg_type, is_response)).start()
