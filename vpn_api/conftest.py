import os
import sys
import tempfile
from pathlib import Path

# Ensure test environment has a SECRET_KEY so importing the app doesn't fail
os.environ.setdefault("SECRET_KEY", "test-secret")
# set PROMOTE_SECRET so tests can use bootstrap promote without needing an existing admin
os.environ.setdefault("PROMOTE_SECRET", "bootstrap-secret")

# Ensure project package is importable when pytest changes cwd
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Use an isolated temporary sqlite DB for tests to avoid conflicts with developer DB files.
tmp_db = Path(tempfile.gettempdir()) / f"vpn_api_test_{os.getpid()}.db"
# Use posix path to avoid backslash issues inside f-strings on Windows
db_url = f"sqlite:///{tmp_db.as_posix()}"
# override DATABASE_URL for the duration of the test session
os.environ.setdefault("DATABASE_URL", db_url)
# Ensure local test runs create the schema via models.Base.metadata.create_all()
# so pytest tests using the app will have tables available without relying on Alembic.
os.environ.setdefault("DEV_INIT_DB", "1")
# remove any stale DB file to start clean
try:
    if tmp_db.exists():
        tmp_db.unlink()
except Exception:
    pass
