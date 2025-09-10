import os

from sqlalchemy import create_engine, inspect

url = os.environ["DATABASE_URL"].replace("+psycopg2", "")
print("using sqlalchemy url:", url)
engine = create_engine(url)
inspector = inspect(engine)
print("tables:", inspector.get_table_names())
