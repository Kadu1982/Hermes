import os
import uuid

os.environ.setdefault("HERMES_DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("HERMES_JWT_SECRET", "test-jwt-secret")
os.environ.setdefault("HERMES_PAIRING_PEPPER", "test-pepper")
os.environ.setdefault("HERMES_CORS_ORIGINS", "http://localhost:3000")
os.environ.setdefault("HERMES_BRAIN_SERVICE_KEY", "test-brain-key")

from app.config import get_settings

get_settings.cache_clear()

import pyotp
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import app
from app.models import User
from app.security import hash_password


@pytest.fixture(scope="function")
def db_engine():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session(db_engine):
    Session = sessionmaker(bind=db_engine, autoflush=False, autocommit=False)
    s = Session()
    yield s
    s.close()


@pytest.fixture(scope="function")
def client(db_session, db_engine):
    def _get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _get_db
    # slowapi needs app.state.limiter bound to this app instance (already global)
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def admin_user(db_session):
    email = "admin@test.com"
    secret = pyotp.random_base32()
    u = User(
        id=uuid.uuid4(),
        email=email,
        password_hash=hash_password("password123"),
        totp_secret=secret,
        totp_confirmed=True,
    )
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)
    totp = pyotp.TOTP(secret)
    code = totp.now()
    return {"user": u, "email": email, "password": "password123", "totp": secret, "code": code}
