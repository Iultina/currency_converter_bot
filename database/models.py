import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship


Base = declarative_base()


class User(Base):
    """
    Класс, представляющий пользователя бота
    """
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    chat_id = Column(Integer, unique=True)
    subscribed = Column(Boolean, default=False)
    history = relationship('History', backref='user')


class History(Base):
    """
    Класс, представляющий историю запросов пользователя
    """
    __tablename__  = 'history'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    date = Column(DateTime, default=datetime.datetime.utcnow)
    rate = Column(Float)
