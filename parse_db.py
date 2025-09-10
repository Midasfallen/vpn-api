#!/usr/bin/env python3
import os
import sys
import urllib.parse as up

u = os.environ.get("DBURL", "")
if not u:
    sys.exit(1)

p = up.urlparse(u)
print("PGHOST=" + (p.hostname or ""))
print("PGPORT=" + (str(p.port) if p.port else ""))
print("PGUSER=" + (p.username or ""))
print("PGPASSWORD=" + (p.password or ""))
print("PGDATABASE=" + (p.path[1:] if p.path else ""))
