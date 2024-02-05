from starlette import status
from starlette.testclient import TestClient

from app.models import User
from app.routers.user import INTERFACE as STATS_INTERFACE


def test_get_user(client: TestClient):
    response = client.get(
        f"/{STATS_INTERFACE}/",
    )

    assert response.status_code == status.HTTP_200_OK

    me = User(**response.json())
    assert me.email == "mholman000@gmail.com"
    assert me.name == "matthew holman"
