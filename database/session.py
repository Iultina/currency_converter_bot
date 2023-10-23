import logging
import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, exc
from sqlalchemy.orm import sessionmaker

from .models import Base

load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

class Config:
    DATABASE_URI = os.getenv('DATABASE_URI', 'postgresql://username:password@localhost:5432/postgres')
    # SQLALCHEMY_TRACK_MODIFICATIONS = False

engine = create_engine(Config.DATABASE_URI)
# engine = create_engine('sqlite:///users.db') 

try:
    Base.metadata.create_all(engine)
except exc.OperationalError as oe:
   logging.error('Ошибка при подключении к базе данных:', oe)
except Exception as e:
    logging.error('Неизвестная ошибка:', e)

Session = sessionmaker(bind=engine)

class DatabaseSession:
    def __init__(self):
        self.session = None

    def __enter__(self):
        self.session = Session()
        return self.session

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.session.close()
