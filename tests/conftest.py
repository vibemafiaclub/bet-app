import pytest
from pathlib import Path
from app import db as db_module


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    """각 테스트마다 별도 temp sqlite file + init_db 실행."""
    db_path = tmp_path / "test.db"
    monkeypatch.setattr(db_module, "DATABASE_PATH", db_path)
    db_module.init_db(db_path)
    yield db_path
