from contextlib import asynccontextmanager

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from tests.fakes import FakeDatabase, FakeMongoClient


@pytest.fixture
def database():
    return FakeDatabase()


@pytest.fixture
def client(database):
    @asynccontextmanager
    async def test_lifespan(application):
        application.state.database = database
        application.state.mongodb_client = FakeMongoClient()
        yield

    with TestClient(create_app(lifespan_context=test_lifespan)) as test_client:
        yield test_client
