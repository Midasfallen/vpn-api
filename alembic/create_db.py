import sys
import os
from pathlib import Path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'vpn_api')))
from database import Base, DB_URL
from sqlalchemy import create_engine


def run():
    # Если DATABASE_URL задан, используем его, иначе используем значение из database.DB_URL
    db_url = os.getenv('DATABASE_URL', DB_URL)
    # Для sqlite убедимся, что директория существует
    if db_url.startswith('sqlite'):
        # Получаем путь к файлу
        if db_url.startswith('sqlite:///'):
            path = db_url.replace('sqlite:///', '')
        else:
            path = db_url.replace('sqlite://', '')
        path = os.path.abspath(path)
        os.makedirs(os.path.dirname(path), exist_ok=True)
    engine = create_engine(db_url)
    Base.metadata.create_all(engine)


if __name__ == '__main__':
    run()
