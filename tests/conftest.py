"""
Shared test setup.

Lets the database-free tests import code that needs psycopg or python-dotenv
on machines where those packages are not installed. When the real packages are
installed (as in the normal dev setup) nothing is replaced.
"""

import importlib.util
import sys
import types


def _stub_missing_driver_modules():
    if importlib.util.find_spec("psycopg") is None:
        psycopg = types.ModuleType("psycopg")
        psycopg.connect = lambda *args, **kwargs: None
        rows = types.ModuleType("psycopg.rows")
        rows.dict_row = object()
        psycopg.rows = rows
        sys.modules["psycopg"] = psycopg
        sys.modules["psycopg.rows"] = rows

    if importlib.util.find_spec("dotenv") is None:
        dotenv = types.ModuleType("dotenv")
        dotenv.load_dotenv = lambda *args, **kwargs: None
        sys.modules["dotenv"] = dotenv


_stub_missing_driver_modules()
