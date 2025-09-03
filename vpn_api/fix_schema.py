import sqlite3
import sys
from pathlib import Path

db_path = Path(__file__).resolve().parent / "test.db"
print("DB path:", db_path)
if not db_path.exists():
    print("Database file does not exist:", db_path)
    sys.exit(1)

conn = sqlite3.connect(str(db_path))
cur = conn.cursor()


def has_column(table, column):
    cur.execute(f"PRAGMA table_info({table})")
    cols = [r[1] for r in cur.fetchall()]
    return column in cols


if not has_column("users", "is_admin"):
    print("Adding column is_admin to users")
    cur.execute("ALTER TABLE users ADD COLUMN is_admin INTEGER DEFAULT 0")
    conn.commit()
else:
    print("Column is_admin already present")

print("Done")
conn.close()
