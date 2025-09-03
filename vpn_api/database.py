import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Единый путь к тестовой локальной БД внутри пакета
default_db_path = Path(__file__).resolve().parent / "test.db"
# Формируем URL в POSIX-формате для кроссплатформенности
default_db_url = f"sqlite:///{default_db_path.as_posix()}"
DB_URL = os.getenv("DATABASE_URL", default_db_url)

if DB_URL.startswith("sqlite"):
    engine = create_engine(DB_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DB_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# Dependency для FastAPI
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
