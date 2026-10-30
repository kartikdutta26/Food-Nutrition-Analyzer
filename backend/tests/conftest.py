from contextlib import asynccontextmanager

import pytest
from fastapi.testclient import TestClient

from app.auth import AuthenticatedUser, get_current_user
from app.database import initialize_database
from app.main import create_app
from tests.fakes import FakeDatabase, FakeMongoClient


TEST_USER_ID = "11111111-1111-4111-8111-111111111111"


@pytest.fixture
def database():
    return FakeDatabase()


@pytest.fixture
def client(database):
    @asynccontextmanager
    async def test_lifespan(application):
        application.state.database = database
        application.state.mongodb_client = FakeMongoClient()
        initialize_database(database)
        yield

    with TestClient(create_app(lifespan_context=test_lifespan)) as test_client:
        yield test_client


@pytest.fixture
def authenticated_client(client):
    """Business-logic tests use a fixed identity; auth behavior has separate tests."""

    client.app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        user_id=TEST_USER_ID
    )
    yield client
    client.app.dependency_overrides.pop(get_current_user, None)
