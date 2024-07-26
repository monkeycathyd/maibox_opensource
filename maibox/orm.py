import logging
import re
from urllib import parse

from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker, declarative_base

import maibox.config as config
from maibox.utils import getLogger

cfg = config.get_config()

_logger = getLogger(__name__)

db_url = f"mysql+pymysql://{cfg['database']['user']}:{parse.quote(cfg['database']['password'])}@{cfg['database']['host']}:{cfg['database']['port']}/{cfg['database']['database']}"
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

class DfBind(Base):
    __tablename__ = "df_bind"
    id = Column(Integer, primary_key=True)
    wxid = Column(String(255))
    df_account = Column(String(511))
    df_password = Column(String(255))
    def __repr__(self):
        return f"<DfBind(wxid={self.wxid}, df_account={self.df_account}, df_password={self.df_password})>"

def get_session():
    Session = sessionmaker(bind=engine)
    return Session()

Base.metadata.create_all(engine)

class Dao:
    def __init__(self):
        self._session = get_session()

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

    def get_df_account(self, wxid: str) -> [str, str]:
        try:
            df_bind = self._session.query(DfBind).filter(DfBind.wxid == wxid).first()
            if not df_bind:
                return None, None
            return df_bind.df_account, df_bind.df_password
        except Exception as e:
            _logger.error(f"Error during get_df_account: {e}")
            self._session.rollback()
            raise e

    def bind_df(self, wxid: str, df_account: str, df_password: str) -> int:
        # if not re.match(r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)", df_account):
        #     return 1
        try:
            if self.get_df_account(wxid) != (None, None):
                return 2
            df_bind = DfBind(wxid=wxid, df_account=df_account, df_password=df_password)
            self._session.add(df_bind)
            self._session.commit()
            return 0
        except Exception as e:
            _logger.error(f"Error during bind_df: {e}")
            self._session.rollback()
            raise e

    def unbind_df(self, wxid: str) -> bool:
        try:
            if not self.get_df_account(wxid):
                return False
            df_bind = self._session.query(DfBind).filter(DfBind.wxid == wxid).first()
            self._session.delete(df_bind)
            self._session.commit()
            return True
        except Exception as e:
            _logger.error(f"Error during unbind_df: {e}")
            self._session.rollback()
            raise e

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