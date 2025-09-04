# tests/conftest.py
import os
import sys
from typing import Generator

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session as SessionClass
from sqlalchemy.orm import sessionmaker
from testcontainers.postgres import PostgresContainer

from app.core.deps import get_db
from app.db.base import Base
from app.main import app
from tests.factories.profile import ProfileFactory
from tests.fixtures.auth import mock_cognito, auth_service, fake_tokens
from tests.fixtures.profile import profile_service, mock_s3, mock_identity


# Ensure project root is importable when running pytest from tests dir or CI
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


# ---- Alembic config helper ----
def get_alembic_config(db_url: str) -> Config:
    """
    Build Alembic Config object, pointing it to the migrations folder.
    """
    cfg = Config(os.path.join(ROOT, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(ROOT, "migrations"))
    cfg.set_main_option("sqlalchemy.url", db_url)
    return cfg


# ---- Start ephemeral Postgres for entire test session ----
@pytest.fixture(scope="session")
def postgres_container():
    """
    Start ephemeral Postgres and yield its connection URL.
    """
    with PostgresContainer("postgres:15", dbname="user_info_test", username="postgres", password="postgres123") as postgres:
        # Give it a short delay to ensure container is ready
        yield postgres.get_connection_url()


@pytest.fixture(scope="session")
def engine(postgres_container):
    """
    Create SQLAlchemy engine and run Alembic migrations on ephemeral DB.
    """
    engine = create_engine(postgres_container)
    # Run Alembic migrations
    alembic_cfg = get_alembic_config(postgres_container)
    command.upgrade(alembic_cfg, "head")
    yield engine
    engine.dispose()


@pytest.fixture(scope="session")
def SessionLocal(engine):
    """
    Session factory bound to test engine.
    """
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session(SessionLocal, engine) -> Generator[SessionClass, None, None]:
    """
    Provide a SQLAlchemy Session wrapped in a SAVEPOINT (nested transaction).
    Each test runs inside an outer transaction which we rollback at the end of the test,
    and a nested savepoint so session.commit() inside the code doesn't persist.
    """
    connection = engine.connect()
    trans = connection.begin()

    session = SessionLocal(bind=connection)
    session.begin_nested()

    # Ensure nested transaction restarts automatically
    @event.listens_for(SessionClass, "after_transaction_end")
    def restart_savepoint(sess, transaction):
        if transaction.nested and not transaction._parent:
            sess.begin_nested()

    try:
        yield session
    finally:
        session.close()
        # trans.rollback()
        connection.close()


@pytest.fixture(scope="function")
def client(db_session: SessionClass) -> Generator[TestClient, None, None]:
    """
    Test client that overrides the app dependency get_db to return the transactional session.
    """
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as c:
            yield c
    finally:
        app.dependency_overrides.clear()


# --- Safety / helpers ---
@pytest.fixture(autouse=True)
def _reset_aws_env(monkeypatch):
    """
    Clear AWS env vars to avoid hitting real AWS services in tests.
    """
    monkeypatch.delenv("AWS_ACCESS_KEY_ID", raising=False)
    monkeypatch.delenv("AWS_SECRET_ACCESS_KEY", raising=False)
    yield


@pytest.fixture(autouse=True)
def _set_factory_session(db_session):
    """
    Wire factory_boy to the session so factories persist to the same transactional session.
    """
    ProfileFactory._meta.sqlalchemy_session = db_session
