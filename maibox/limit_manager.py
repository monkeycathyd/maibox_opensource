from maibox.orm import Dao
from maibox.config import get_config

cfg = get_config()

class LimitManager:
    def __init__(self, dao: Dao, action_type: str):
        self.dao = dao
        self.action_type = action_type

    def is_reached_limit(self, trackable_significant: str, max_usage: int, period: int) -> bool:
        return self.dao.is_reached_limit(trackable_significant, self.action_type, max_usage, period)

    def reset_limit(self, trackable_significant: str, period: int) -> bool:
        return self.dao.reset_limit(trackable_significant, self.action_type, period)

    def add_usage_count(self, trackable_significant: str, period: int, usage_count: int=1) -> bool:
        return self.dao.add_usage_count(trackable_significant, self.action_type, usage_count, period)

    def get_usage_count(self, trackable_significant: str, period: int) -> int:
        return self.dao.get_usage_count(trackable_significant, self.action_type, period)
