from maibox.orm import Dao
from maibox.config import get_config

cfg = get_config()

class LimitManager:
    def __init__(self, dao: Dao, action_type: str):
        self.dao = dao
        self.action_type = action_type

