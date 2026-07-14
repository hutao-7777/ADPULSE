"""Authentication API integration tests."""

from typing import Any, cast

import pytest

from app.core.security import create_refresh_token

pytestmark = pytest.mark.asyncio


def _unwrap(resp) -> dict[str, Any]:
    return cast(dict[str, Any], resp.json()["data"])


async def _login_admin(client) -> dict:
    resp = await client.post(
        "/api/auth/login",
        json={"email": "admin@example.com", "password": "admin123"},
    )
    assert resp.status_code == 200
    return _unwrap(resp)


async def test_auth_login_and_profile(client):
    tokens = await _login_admin(client)
    assert "access_token" in tokens
    assert tokens["token_type"] == "bearer"

    me = await client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert me.status_code == 200
    assert _unwrap(me)["email"] == "admin@example.com"


async def test_auth_register_refresh_and_api_keys(client):
    admin = await _login_admin(client)
    admin_token = admin["access_token"]

    register = await client.post(
        "/api/auth/register",
        json={"email": "advertiser@example.com", "password": "secret123"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert register.status_code == 201

    user_tokens = await client.post(
        "/api/auth/login",
        json={"email": "advertiser@example.com", "password": "secret123"},
    )
    assert user_tokens.status_code == 200
    refresh_token_val = _unwrap(user_tokens)["refresh_token"]

    refreshed = await client.post(
        "/api/auth/refresh", json={"refresh_token": refresh_token_val}
    )
    assert refreshed.status_code == 200
    assert "access_token" in _unwrap(refreshed)

    key_resp = await client.post(
        "/api/auth/api-keys",
        json={"name": "dsp-test", "scopes": ["rtb:write"]},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert key_resp.status_code == 201
    raw_key = _unwrap(key_resp)["key"]

    list_resp = await client.get(
        "/api/auth/api-keys", headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert list_resp.status_code == 200
    assert any(k["name"] == "dsp-test" for k in _unwrap(list_resp))

    check = await client.get("/api/auth/api-key-check", headers={"X-API-Key": raw_key})
    assert check.status_code == 200
    assert _unwrap(check)["valid"] is True

    # A refresh token that was never persisted should not be refreshable.
    unstored_token, _ = create_refresh_token(_unwrap(register)["id"])
    bad_refresh = await client.post(
        "/api/auth/refresh", json={"refresh_token": unstored_token}
    )
    assert bad_refresh.status_code == 401
