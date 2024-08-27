import datetime
from urllib import parse

from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Boolean, Double
from sqlalchemy.orm import sessionmaker, declarative_base

import maibox.manager.config as config
from maibox.util.utils import getLogger

cfg = config.get_config()

_logger = getLogger(__name__)

if cfg['database']["type"] == "mysql":
    db_url = f"mysql+pymysql://{cfg['database']['user']}:{parse.quote(cfg['database']['password'])}@{cfg['database']['host']}:{cfg['database']['port']}/{cfg['database']['database']}"
else:
    db_url = f"sqlite:///./{cfg['database']['database']}.db"
engine = create_engine(db_url, echo=False)

Base = declarative_base()

class Bind(Base):
    __tablename__ = "bind"
    id = Column(Integer, primary_key=True)
    uid = Column(Integer)
    wxid = Column(String(255))
    def __repr__(self):
        return f"<Bind(uid={self.uid}, wxid={self.wxid})>"

class Whitelist(Base):
    __tablename__ = "whitelist"
    id = Column(Integer, primary_key=True)
    uid = Column(Integer)
    def __repr__(self):
        return f"<Whitelist(uid={self.uid})>"

class DfBindNew(Base):
    __tablename__ = "df_bind_new"
    id = Column(Integer, primary_key=True)
    wxid = Column(String(255))
    df_token = Column(String(511))
    def __repr__(self):
        return f"<DfBind(wxid={self.wxid}, df_account={self.df_token})>"

class ActionLimit(Base):
    __tablename__ = "action_limit"
    id = Column(Integer, primary_key=True)
    trackable_significant = Column(String(255), nullable=False)
    action_type = Column(String(255), nullable=False)
    usage_count = Column(Integer, default=0)
    period_first_start_time = Column(DateTime, default=datetime.datetime.min)
    next_reset_time = Column(DateTime, default=datetime.datetime.max)
    def __repr__(self):
        return f"<ActionLimit(wxid={self.trackable_significant}, action_type={self.action_type}, usage_count={self.usage_count}, period_first_start_time={self.period_first_start_time}, next_reset_time={self.next_reset_time})>"

class MsgRecords(Base):
    __tablename__ = "msg_records"
    id = Column(Integer, primary_key=True)
    date = Column(DateTime, default=datetime.datetime.now)
    wxid = Column(String(255))
    msg_type = Column(String(255))
    msg_body = Column(Text)
    is_response = Column(Boolean, nullable=False)

    def __repr__(self):
        return f"<MsgRecords(wxid={self.wxid}, msg_type={self.msg_type}, msg_body={self.msg_body}, is_response={self.is_response})>"

class NetworkRecords(Base):
    __tablename__ = "network_records"
    id = Column(Integer, primary_key=True)
    date = Column(DateTime, default=datetime.datetime.now)
    endpoint = Column(Text, nullable=False)
    delay = Column(Double, default=0)
    is_failed = Column(Boolean, default=False)
    is_zlib_skip = Column(Boolean, default=False)


def get_session():
    return sessionmaker(bind=engine)()

Base.metadata.create_all(engine)

class Dao:
    def __init__(self):
        self._session = get_session()

    def add_network_records(self, endpoint: str, delay: int=0, is_failed: bool=False, is_zlib_skip: bool=False):
        try:
            self._session.add(NetworkRecords(endpoint=endpoint, delay=delay, is_failed=is_failed, is_zlib_skip=is_zlib_skip))
            self._session.commit()
            return True
        except Exception as e:
            self._session.rollback()
            _logger.error(f"Error during add_network_records: {e}")
            return False

    def get_network_records(self):
        try:
            return [{
                "id": record.id,
                "date": record.date,
                "endpoint": record.endpoint,
                "delay": record.delay,
                "is_failed": record.is_failed,
                "is_zlib_skip": record.is_zlib_skip
            } for record in self._session.query(NetworkRecords).all()]
        except Exception as e:
            _logger.error(f"Error during get_network_records: {e}")
            return []

    def add_record(self, wxid: str, msg_body: str, msg_type: str="text", is_response: bool=False) -> bool:
        try:
            self._session.add(MsgRecords(wxid=wxid, msg_body=msg_body, msg_type=msg_type, is_response=is_response))
            self._session.commit()
            return True
        except Exception as e:
            self._session.rollback()
            _logger.error(f"Error during add_record: {e}")
            return False

    def get_all_records(self, limit: int=100, offset: int=0):
        try:
            records = self._session.query(MsgRecords).order_by(MsgRecords.date.desc()).limit(limit).offset(offset).all()
            _logger.info(f"get {len(records)} records")
            return {
                "next_offset": offset + limit,
                "limit": limit,
                "is_end": len(records) < limit,
                "records": [
                    {
                        "id": record.id,
                        "wxid": record.wxid,
                        "date": record.date,
                        "msg_body": record.msg_body
                    } for record in records
                ]
            }
        except Exception as e:
            self._session.rollback()
            _logger.error(f"Error during get_all_records: {e}")
            return {
                "next_offset": -1,
                "limit": -1,
                "is_end": True,
                "records": []
            }

    def get_records_wxid(self, wxid: str, limit: int=100, offset: int=0):
        try:
            records = self._session.query(MsgRecords).filter(MsgRecords.wxid == wxid).order_by(MsgRecords.date.desc()).limit(limit).offset(offset).all()
            _logger.info(f"get {len(records)} records")
            return {
                "next_offset": offset + limit,
                "limit": limit,
                "is_end": len(records) < limit,
                "records": [
                    {
                        "id": record.id,
                        "wxid": record.wxid,
                        "date": record.date,
                        "msg_body": record.msg_body
                    } for record in records
                ]
            }
        except Exception as e:
            self._session.rollback()
            _logger.error(f"Error during get_records_wxid: {e}")
            return {
                "next_offset": -1,
                "limit": -1,
                "is_end": True,
                "records": []
            }

    def get_records_date_range(self, start_date: datetime.datetime=datetime.datetime.min, end_date: datetime.datetime=datetime.datetime.now(), limit: int=100, offset: int=0):
        try:
            _logger.info(f"get records between {start_date} and {end_date}")
            records = self._session.query(MsgRecords).filter(MsgRecords.date >= start_date, MsgRecords.date <= end_date).order_by(MsgRecords.date.desc()).limit(limit).offset(offset).all()
            _logger.info(f"get {len(records)} records")
            return {
                "next_offset": offset + limit,
                "limit": limit,
                "is_end": len(records) < limit,
                "records": [
                    {
                        "id": record.id,
                        "wxid": record.wxid,
                        "date": record.date,
                        "msg_body": record.msg_body
                    } for record in records
                ]
            }
        except Exception as e:
            self._session.rollback()
            _logger.error(f"Error during get_records_date_range: {e}")
            return {
                "next_offset": -1,
                "limit": -1,
                "is_end": True,
                "records": []
            }

    def getUid(self, wxid: str) -> int:
        try:
            bind = self._session.query(Bind).filter(Bind.wxid == wxid).first()
            return bind.uid
        except Exception as e:
            _logger.error(f"Error during bind: {e}")
            self._session.rollback()
            return 0

    def bind(self, uid: int, wxid: str) -> int:
        try:
            if self.getUid(wxid):
                return 0
            bind = Bind(uid=uid, wxid=wxid)
            self._session.add(bind)
            self._session.commit()
            return uid
        except Exception as e:
            _logger.error(f"Error during bind: {e}")
            self._session.rollback()
            return 0

    def unbind(self, wxid: str) -> bool:
        try:
            if not self.getUid(wxid):
                return False
            bind = self._session.query(Bind).filter(Bind.wxid == wxid).first()
            self._session.delete(bind)
            self._session.commit()
            return True
        except Exception as e:
            _logger.error(f"Error during unbind: {e}")
            self._session.rollback()
            return False
    def get_df_token(self, wxid: str) -> str:
        try:
            df_bind = self._session.query(DfBindNew).filter(DfBindNew.wxid == wxid).first()
            if not df_bind:
                return ""
            return str(df_bind.df_token)
        except Exception as e:
            _logger.error(f"Error during get_df_token: {e}")
            self._session.rollback()
            raise e

    def bind_df_token(self, wxid: str, df_token: str) -> int:
        try:
            df_bind = DfBindNew(wxid=wxid, df_token=df_token)
            self._session.add(df_bind)
            self._session.commit()
            return 0
        except Exception as e:
            _logger.error(f"Error during bind_df_token: {e}")
            self._session.rollback()
            raise e

    def unbind_df_token(self, wxid: str) -> bool:
        try:
            if not self.get_df_token(wxid):
                return False
            df_bind = self._session.query(DfBindNew).filter(DfBindNew.wxid == wxid).first()
            self._session.delete(df_bind)
            self._session.commit()
            return True
        except Exception as e:
            _logger.error(f"Error during unbind_df_token: {e}")

    def getAllWhitelist(self) -> list:
        try:
            whitelist = self._session.query(Whitelist).all()
            return [str(w.uid) for w in whitelist]
        except Exception as e:
            _logger.error(f"Error during get_white_list: {e}")
            self._session.rollback()
            raise e

    def isWhitelist(self, uid: int) -> bool:
        try:
            return str(uid) in self.getAllWhitelist()
        except Exception as e:
            _logger.error(f"Error during is_white_list: {e}")
            self._session.rollback()
            raise e

    def addWhitelist(self, uid: int) -> bool:
        try:
            if str(uid) in self.getAllWhitelist():
                return False
            whitelist = Whitelist(uid=uid)
            self._session.add(whitelist)
            self._session.commit()
            return True
        except Exception as e:
            _logger.error(f"Error during add_white_list: {e}")
            self._session.rollback()
            raise e

    def removeWhitelist(self, uid: int) -> bool:
        try:
            if str(uid) not in self.getAllWhitelist():
                return False
            whitelist = self._session.query(Whitelist).filter(Whitelist.uid == uid).first()
            self._session.delete(whitelist)
            self._session.commit()
            return True
        except Exception as e:
            _logger.error(f"Error during remove_white_list: {e}")
            self._session.rollback()
            raise e

    def add_usage_count(self, trackable_significant: str, action_type: str, usage_count: int, period: int):
        try:
            action_limit = self._session.query(ActionLimit).filter(ActionLimit.trackable_significant == trackable_significant, ActionLimit.action_type == action_type).first()
            if not action_limit:
                action_limit = ActionLimit(trackable_significant=trackable_significant, action_type=action_type)
                self._session.add(action_limit)
                self._session.commit()
            action_limit.usage_count += usage_count
            action_limit.period_first_start_time = datetime.datetime.now()
            action_limit.next_reset_time = datetime.datetime.now() + datetime.timedelta(hours=period)
            self._session.commit()
            return True
        except Exception as e:
            _logger.error(f"Error during add_usage_count: {e}")
            self._session.rollback()
            raise e

    def reset_limit(self, trackable_significant: str, action_type: str, period: int):
        try:
            action_limit = self._session.query(ActionLimit).filter(ActionLimit.trackable_significant == trackable_significant, ActionLimit.action_type == action_type).first()
            if not action_limit:
                return False
            action_limit.usage_count = 0
            action_limit.period_first_start_time = datetime.datetime.now()
            action_limit.next_reset_time = datetime.datetime.now() + datetime.timedelta(hours=period)
            self._session.commit()
            return True
        except Exception as e:
            _logger.error(f"Error during reset_limit: {e}")
            self._session.rollback()
            raise e

    def is_reached_limit(self, trackable_significant: str, action_type: str, max_usage: int, period: int):
        try:
            action_limit = self.get_usage_count(trackable_significant, action_type, period)
            return action_limit >= max_usage
        except Exception as e:
            _logger.error(f"Error during is_reached_limit: {e}")
            self._session.rollback()
            raise e

    def get_usage_count(self, trackable_significant: str, action_type: str, period: int):
        try:
            action_limit = self._session.query(ActionLimit).filter(ActionLimit.trackable_significant == trackable_significant, ActionLimit.action_type == action_type).first()
            if not action_limit:
                return 0
            if action_limit.next_reset_time <= datetime.datetime.now():
                self.reset_limit(trackable_significant, action_type, period)
                return 0
            return action_limit.usage_count
        except Exception as e:
            _logger.error(f"Error during get_usage_count: {e}")
            self._session.rollback()
            raise e