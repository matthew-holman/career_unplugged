from datetime import datetime, timedelta, timezone

from sqlmodel import Session
from starlette import status
from starlette.testclient import TestClient

from app.models.career_page import CareerPage


def test_list_career_pages_filters(
    authed_client: TestClient, db_session: Session
) -> None:
    now = datetime.now(timezone.utc)
    older = now - timedelta(days=5)

    pages = [
        CareerPage(
            company_name="Acme",
            url="https://careers.acme.com",
            active=True,
            last_synced_at=now,
        ),
        CareerPage(
            company_name="Beta",
            url="https://jobs.beta.com",
            active=False,
            deactivated_at=older,
            last_status_code=404,
        ),
        CareerPage(
            company_name="Gamma",
            url="https://jobs.gamma.com",
            active=True,
            last_synced_at=older,
            last_status_code=403,
        ),
    ]
    for page in pages:
        db_session.add(page)
    db_session.commit()

    response = authed_client.get("/career-pages/", params={"company_name": "acme"})
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) == 1
    assert response.json()[0]["company_name"] == "Acme"

    response = authed_client.get("/career-pages/", params={"active": False})
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) == 1
    assert response.json()[0]["company_name"] == "Beta"

    response = authed_client.get("/career-pages/", params={"last_status_code": 404})
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) == 1
    assert response.json()[0]["company_name"] == "Beta"

    response = authed_client.get(
        "/career-pages/",
        params={
            "last_synced_at_gte": older.isoformat(),
            "last_synced_at_lte": now.isoformat(),
        },
    )
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) == 2

    response = authed_client.get("/career-pages/", params={"url": "gamma"})
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) == 1
    assert response.json()[0]["company_name"] == "Gamma"
