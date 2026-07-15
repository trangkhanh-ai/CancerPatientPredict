# -*- coding: utf-8 -*-
"""Dependency injection cho FastAPI: cung cấp MongoDB database (dùng chung client)."""
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from mongodb.client import get_db as _get_db  # noqa: E402


def get_db():
    """Trả về database MongoDB. Dùng qua Depends(get_db)."""
    return _get_db()
