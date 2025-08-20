import sqlite3
from pathlib import Path

db_path = Path(__file__).resolve().parent / 'test.db'
print('test.db exists:', db_path.exists())
if db_path.exists():
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    print('\nPRAGMA table_info(users):')
    for row in cur.execute("PRAGMA table_info('users')"):
        print(row)
    print('\nSample rows:')
    try:
        for row in cur.execute('SELECT id, email, status, is_admin FROM users LIMIT 5'):
            print(row)
    except Exception as e:
        print('Could not read sample rows:', e)
    conn.close()
else:
    print('no db file')
