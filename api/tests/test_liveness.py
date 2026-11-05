from api.main import app
from fastapi.testclient import TestClient


client = TestClient(app)


def test_liveness():
    response = client.get('/')

    assert response.status_code == 204

