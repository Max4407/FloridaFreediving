from datetime import UTC, datetime

import bcrypt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from config import Settings, get_settings
from database import Base, get_db
from main import app

TEST_SETTINGS = Settings(
    database_url="sqlite://",
    officer_password_hash=bcrypt.hashpw(b"club-password", bcrypt.gensalt()).decode(),
    session_secret="test-session-secret-that-is-long-enough",
    cookie_secure=False,
    allowed_origins="http://testserver",
)


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as session:
        yield session
    Base.metadata.drop_all(engine)


@pytest.fixture
def client(db):
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_settings] = lambda: TEST_SETTINGS
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def officer_client(client):
    response = client.post(
        "/api/auth/login",
        json={"password": "club-password"},
        headers={"Origin": "http://testserver"},
    )
    assert response.status_code == 200
    return client


@pytest.fixture
def dive_payload():
    return {
        "title": "Blue Heron Bridge",
        "description": "Meet by the east beach.",
        "location": "Riviera Beach, FL",
        "starts_at": datetime(2030, 9, 12, 8, 0, tzinfo=UTC).isoformat(),
        "capacity": 1,
        "officer_ids": [],
    }
