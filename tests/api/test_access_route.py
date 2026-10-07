from unittest.mock import patch

from api.auth.rbac import UnknownUserError


def test_access_known_user(client):
    with patch("api.routes.access.get_role", return_value="admin"):
        resp = client.get("/access", params={"username": "Hsuan AD"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["role"] == "admin"
    assert set(body["allowed_domains"]) == {"hr_rag", "sales_sql", "github"}


def test_access_unknown_user(client):
    with patch("api.routes.access.get_role", side_effect=UnknownUserError("nope")):
        resp = client.get("/access", params={"username": "ghost"})
    assert resp.status_code == 404


def test_access_requires_username(client):
    resp = client.get("/access")
    assert resp.status_code == 422
