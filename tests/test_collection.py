import pytest
import uuid

@pytest.mark.asyncio
async def test_add_to_collection(client, test_user, test_movies):
    user, token = test_user
    movie = test_movies[0]
    response = await client.post(
        "/api/collection/add",
        json={"movie_id": str(movie.id)},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == movie.title
    assert data["status"] == "will_watch"

@pytest.mark.asyncio
async def test_add_existing_movie_to_collection(client, test_user, test_movies):
    user, token = test_user
    movie = test_movies[0]
    await client.post(
        "/api/collection/add",
        json={"movie_id": str(movie.id)},
        headers={"Authorization": f"Bearer {token}"}
    )
    response = await client.post(
        "/api/collection/add",
        json={"movie_id": str(movie.id)},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 400
    assert "Movie already in collection" in response.json()["detail"]

@pytest.mark.asyncio
async def test_update_movie_status(client, test_user, test_movies):
    user, token = test_user
    movie = test_movies[0]
    add_response = await client.post(
        "/api/collection/add",
        json={"movie_id": str(movie.id)},
        headers={"Authorization": f"Bearer {token}"}
    )
    user_movie_id = add_response.json()["id"]
    response = await client.post(
        f"/api/collection/{user_movie_id}/watched",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "watched"

@pytest.mark.asyncio
async def test_update_nonexistent_movie_status(client, test_user):
    user, token = test_user
    fake_id = uuid.uuid4()
    response = await client.post(
        f"/api/collection/{fake_id}/watched",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 404
    assert "Movie not found in collection" in response.json()["detail"]

@pytest.mark.asyncio
async def test_get_collection(client, test_user, test_movies):
    user, token = test_user
    for movie in test_movies:
        await client.post(
            "/api/collection/add",
            json={"movie_id": str(movie.id)},
            headers={"Authorization": f"Bearer {token}"}
        )
    response = await client.get(
        "/api/collection/",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == len(test_movies)

@pytest.mark.asyncio
async def test_get_collection_unauthorized(client):
    response = await client.get("/api/collection/")
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_delete_from_collection(client, test_user, test_movies):
    user, token = test_user
    movie = test_movies[0]
    add_response = await client.post(
        "/api/collection/add",
        json={"movie_id": str(movie.id)},
        headers={"Authorization": f"Bearer {token}"}
    )
    user_movie_id = add_response.json()["id"]
    response = await client.delete(
        f"/api/collection/{user_movie_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 204

@pytest.mark.asyncio
async def test_delete_nonexistent_from_collection(client, test_user):
    user, token = test_user
    fake_id = uuid.uuid4()
    response = await client.delete(
        f"/api/collection/{fake_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 404