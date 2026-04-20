from fastapi.testclient import TestClient
from app.main import app
from app.db import get_db
from tests.mock_db import MockNeo4jService

client = TestClient(app)


def test_earthquakes():
    app.dependency_overrides[get_db] = lambda: MockNeo4jService()

    response = client.get("/earthquakes?limit=2")

    assert response.status_code == 200
    assert len(response.json()) == 2


def teardown_function():
    app.dependency_overrides = {}

# ✅ EDGE CASE
class MockNeo4jServiceEmpty:
    def run(self, query, **params):
        return []


def test_earthquakes_empty():
    app.dependency_overrides[get_db] = lambda: MockNeo4jServiceEmpty()

    response = client.get("/earthquakes")

    assert response.status_code == 200
    assert response.json() == []