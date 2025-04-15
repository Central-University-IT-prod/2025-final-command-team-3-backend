import pytest
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_search_movies(client, test_user, test_movies, mock_es):
    user, token = test_user
    mock_es.search.return_value = {
        "hits": {"hits": [{"_id": str(movie.id)} for movie in test_movies]}
    }
    response = await client.get(
        "/api/movies/search?title=Movie",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == len(test_movies)

@pytest.mark.asyncio
async def test_search_movies_invalid_genre(client, test_user):
    user, token = test_user
    response = await client.get(
        "/api/movies/search?genres=invalid",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 400
    assert "Invalid genre" in response.json()["detail"]

@pytest.mark.asyncio
async def test_get_top_movies(client, test_user, test_movies):
    user, token = test_user
    response = await client.get(
        "/api/movies/top",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0

@pytest.mark.asyncio
async def test_get_top_movies_unauthorized(client):
    response = await client.get("/api/movies/top")
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_get_recommended_movies(client, test_user, test_movies):
    user, token = test_user
    response = await client.get(
        "/api/movies/recommended",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0

@pytest.mark.asyncio
async def test_get_recommended_movies_unauthorized(client):
    response = await client.get("/api/movies/recommended")
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_reindex_movies_admin(client, admin_user, test_movies, mock_es):
    admin, token = admin_user
    mock_es.indices.exists.return_value = True
    mock_es.indices.delete.return_value = None
    mock_es.indices.create.return_value = None
    from elasticsearch.helpers import async_bulk
    with patch('elasticsearch.helpers.async_bulk', new_callable=AsyncMock) as mock_bulk:
        mock_bulk.return_value = (len(test_movies), [])
        response = await client.post(
            "/api/movies/reindex",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total_movies"] == len(test_movies)

@pytest.mark.asyncio
async def test_reindex_movies_non_admin(client, test_user):
    user, token = test_user
    response = await client.post(
        "/api/movies/reindex",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 403
    assert "Only admin users can reindex movies" in response.json()["detail"]

@pytest.mark.asyncio
async def test_extract_metadata_valid_url(client):
    with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.text = """
        <html>
            <head>
                <meta property="og:title" content="Test Title">
                <meta property="og:description" content="Test Description">
                <meta property="og:image" content="http://example.com/image.jpg">
            </head>
        </html>
        """
        mock_get.return_value = mock_response
        response = await client.get("/api/movies/extract-metadata?url=http://example.com")
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Test Title"
        assert data["overview"] == "Test Description"
        assert data["poster_url"] == "http://example.com/image.jpg"

@pytest.mark.asyncio
async def test_extract_metadata_invalid_url(client):
    with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = Exception("Network error")
        response = await client.get("/api/movies/extract-metadata?url=invalid_url")
        assert response.status_code == 400
        assert "Failed to fetch URL" in response.json()["detail"]
