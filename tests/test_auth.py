import pytest

@pytest.mark.asyncio
async def test_register_new_user(client):
    response = await client.post("/api/auth/register", json={
        "email": "newuser@example.com",
        "password": "StrongPass1!"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

@pytest.mark.asyncio
async def test_register_existing_email(client, test_user):
    user, _ = test_user
    response = await client.post("/api/auth/register", json={
        "email": user.email,
        "password": "AnotherPass1!"
    })
    assert response.status_code == 400
    assert "Email already exists" in response.json()["detail"]

@pytest.mark.asyncio
async def test_login_correct_credentials(client, test_user):
    user, _ = test_user
    response = await client.post("/api/auth/login", data={
        "email": user.email,
        "password": "TestPass1!"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

@pytest.mark.asyncio
async def test_login_incorrect_password(client, test_user):
    user, _ = test_user
    response = await client.post("/api/auth/login", data={
        "email": user.email,
        "password": "WrongPass!"
    })
    assert response.status_code == 401
    assert "Invalid email or password" in response.json()["detail"]