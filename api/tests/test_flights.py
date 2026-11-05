import mongomock
from api.main import app
from api.dependencies import get_db_client
from fastapi.testclient import TestClient


mocked_client = mongomock.MongoClient()


def override_db_client():
    client = mocked_client
    return client


app.dependency_overrides[get_db_client] = override_db_client

client = TestClient(app)


def test_create_and_list_flight():
    # Create

    response = client.post(
        '/flights',
        json={'status': "scheduled"}
    )

    assert response.status_code == 200, response.text
    data = response.json()

    assert "id" in data
    assert data["status"] == "scheduled"

    flight_id = data["id"]

    # List

    response = client.get('/flights')

    assert response.status_code == 200, response.text
    data = response.json()

    assert data[0]["id"] == flight_id
