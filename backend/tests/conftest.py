import os
import pathlib

_test_db = pathlib.Path("/tmp/etl_stats_pytest.sqlite")
if _test_db.exists():
    _test_db.unlink()
os.environ.setdefault("DATABASE_URL", f"sqlite:///{_test_db}")
os.environ.setdefault("STATS_API_TOKEN", "testtoken")
