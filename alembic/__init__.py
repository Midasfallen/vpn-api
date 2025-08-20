import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'vpn_api')))
from database import Base
import models

def run():
    from sqlalchemy import create_engine
    db_url = os.getenv("DATABASE_URL", "sqlite:///../vpn_api/test.db")
    engine = create_engine(db_url)
    Base.metadata.create_all(engine)

if __name__ == "__main__":
    run()
