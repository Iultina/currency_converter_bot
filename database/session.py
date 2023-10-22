import os
from sqlalchemy import create_engine, exc
from sqlalchemy.orm import sessionmaker
from .models import Base
from dotenv import load_dotenv

load_dotenv()
print(os.getenv('DATABASE_URI'))

class Config:
    DATABASE_URI = os.getenv('DATABASE_URI', 'postgresql://username:password@localhost:5432/postgres')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

engine = create_engine(Config.DATABASE_URI)

try:
    Base.metadata.create_all(engine)
except exc.OperationalError as oe:
    print("Ошибка при подключении к базе данных:", oe)
except Exception as e:
    print("Неизвестная ошибка:", e)

Session = sessionmaker(bind=engine)

class DatabaseSession:
    def __init__(self):
        self.session = None

    def __enter__(self):
        self.session = Session()
        return self.session

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.session.close()
