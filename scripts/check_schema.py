"""Simple schema inspection helper for the local sqlite test DB.

Run manually during development. Not used in CI.
"""

import os
import sqlite3

p = os.path.abspath("vpn_api/test.db")
print("DB:", p)

con = sqlite3.connect(p)
cur = con.cursor()

for t in ["users", "tariffs", "user_tariffs", "vpn_peers", "payments"]:
    try:
        cur.execute(f"PRAGMA table_info('{t}')")
        cols = cur.fetchall()
        print("\n", t, "columns:")
        for c in cols:
            print(" ", c[1], c[2])
    except Exception as e:
        print("Error reading", t, e)

con.close()
