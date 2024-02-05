from starlette import status
from starlette.testclient import TestClient

from app.models import HelloWorld
from app.routers.hello_world import INTERFACE as STATS_INTERFACE


def test_get_hello_world(client: TestClient):
    response = client.get(
        f"/{STATS_INTERFACE}/",
    )

    assert response.status_code == status.HTTP_200_OK

    hello_world = HelloWorld(**response.json())
    assert hello_world.hello is True
    assert hello_world.world == "earth"
