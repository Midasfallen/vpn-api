import sqlite3, os
print('test.db exists:', os.path.exists('test.db'))
if os.path.exists('test.db'):
    conn = sqlite3.connect('test.db')
    cur = conn.cursor()
    print('\nPRAGMA table_info(users):')
    for row in cur.execute("PRAGMA table_info('users')"):
        print(row)
    print('\nSample rows:')
    for row in cur.execute('SELECT id, email, status, is_admin FROM users LIMIT 5'):
        print(row)
    conn.close()
else:
    print('no db file')
