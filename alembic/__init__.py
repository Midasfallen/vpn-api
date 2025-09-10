import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "vpn_api")))
import models
from database import Base


def run():
    from sqlalchemy import create_engine

    db_url = os.getenv("DATABASE_URL", "sqlite:///../vpn_api/test.db")
    engine = create_engine(db_url)
    Base.metadata.create_all(engine)


if __name__ == "__main__":
    run()
