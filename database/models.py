from sqlalchemy import Boolean, Column, Integer, Float, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import datetime


Base = declarative_base()


class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    chat_id = Column(Integer, unique=True)
    subscribed = Column(Boolean, default=False)
    history = relationship('History', backref='user')


class History(Base):
    __tablename__  = 'history'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    date = Column(DateTime, default=datetime.datetime.utcnow)
    rate = Column(Float)
