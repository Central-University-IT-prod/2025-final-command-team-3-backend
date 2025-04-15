import pytest
from io import BytesIO
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_get_image(client, test_user, mock_minio_client):
    user, token = test_user
    filename = "test_image.jpg"
    response = await client.get(f"/api/images/{filename}")
    assert response.status_code == 307  # Redirect
    assert response.headers["location"].startswith("https://prod-team-3-uad8jq68.REDACTED:8005")

@pytest.mark.asyncio
async def test_get_nonexistent_image(client, mock_minio_client):
    mock_minio_client.stat_object.side_effect = Exception("Not found")
    with patch('aiohttp.ClientSession.get', new_callable=AsyncMock) as mock_get:
        mock_response = AsyncMock()
        mock_response.status = 404
        mock_get.return_value.__aenter__.return_value = mock_response
        response = await client.get("/api/images/nonexistent.jpg")
        assert response.status_code == 404

@pytest.mark.asyncio
async def test_upload_image(client, test_user, mock_minio_client):
    user, token = test_user
    image_content = b"fake image data"
    response = await client.post(
        "/api/images/upload",
        files={"file": ("test_image.jpg", BytesIO(image_content), "image/jpeg")},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "url" in data

@pytest.mark.asyncio
async def test_upload_non_image(client, test_user):
    user, token = test_user
    text_content = b"not an image"
    response = await client.post(
        "/api/images/upload",
        files={"file": ("test.txt", BytesIO(text_content), "text/plain")},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 400
    assert "File must be an image" in response.json()["detail"]
