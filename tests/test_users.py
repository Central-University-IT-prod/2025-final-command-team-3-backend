import pytest

@pytest.mark.asyncio
async def test_get_user_info(client, test_user):
    user, token = test_user
    response = await client.get(
        "/api/user/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == user.email
    assert data["username"] == user.username

@pytest.mark.asyncio
async def test_get_user_info_unauthorized(client):
    response = await client.get("/api/user/me")
    assert response.status_code == 401