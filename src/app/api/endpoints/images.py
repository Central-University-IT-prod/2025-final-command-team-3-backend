import hashlib
import io
import uuid
import aiohttp
from app.core.minio_client import minio_client
from app.core.security import get_current_user
from app.models.user import User
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status, Query
from app.core.config import settings
from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/api/images", tags=["images"])


async def fetch_image_with_proxy(image_url: str):
    async with aiohttp.ClientSession() as session:
        async with session.get(image_url, proxy=settings.PROXY) as resp:
            if resp.status == 200:
                return await resp.read(), resp.content_type
            else:
                raise HTTPException(status_code=resp.status, detail=await resp.text())

async def upload_to_minio(filename: str, content: bytes, content_type: str):
    try:
        minio_client.put_object(
            settings.MINIO_BUCKET_NAME,
            filename,
            io.BytesIO(content),
            length=len(content),
            content_type=content_type,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload file: {str(e)}"
        )

def stream_from_minio(filename: str):
    """Synchronous function to fetch and stream content from MinIO with content type."""
    try:
        # Get object metadata to retrieve content type
        stat = minio_client.stat_object(settings.MINIO_BUCKET_NAME, filename)
        content_type = stat.content_type  # Content type from metadata

        # Get the object data for streaming
        response = minio_client.get_object(settings.MINIO_BUCKET_NAME, filename)
        
        def generate():
            try:
                for chunk in response.stream(amt=8192):  # Stream in 8KB chunks
                    yield chunk
            finally:
                response.close()
                response.release_conn()
        return generate(), content_type
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch file: {str(e)}"
        )


async def upload_from_url(image_url: str):
    """
    Upload an image from a URL with caching.
    """
    try:
        # Generate a unique filename based on the URL hash
        url_hash = hashlib.sha256(image_url.encode()).hexdigest()
        file_extension = image_url.split('.')[-1] if '.' in image_url else 'jpg'
        if not file_extension.isalpha():
            file_extension = file_extension.split('?')[0]
        filename = f"{url_hash}.{file_extension}" if file_extension else url_hash

        # Check if the file already exists in MinIO (cache)
        try:
            minio_client.stat_object(settings.MINIO_BUCKET_NAME, filename)
            # File exists, return the URL
            return f"/{filename}"
        except Exception as e:
            # File does not exist, proceed to download and upload
            print(f"File not found in MinIO; downloading from URL: {image_url}")

        # Fetch the image from the provided URL
        content, content_type = await fetch_image_with_proxy(image_url)

        # Upload the image to MinIO
        await upload_to_minio(filename, content, content_type)

        # Return the URL to access the uploaded image
        return f"/{filename}"
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload image from URL: {str(e)}"
        )

@router.get("/{filename}")
async def get_file(filename: str):
    """
    Get TMDB and user uploaded images.
    """
    filename = filename.lstrip('/')

    # Check if minio has the file
    try:
        minio_client.stat_object(settings.MINIO_BUCKET_NAME, filename)

        # File exists, stream it from MinIO
        stream, content_type = stream_from_minio(filename)
        return StreamingResponse(stream, media_type=content_type)
    except Exception as e:
        print("file not found in minio; fetching tmdb", str(e))

        # Could be a TMDB image
        try:
            TMDB_IMAGE_API = "http://image.tmdb.org/t/p/w500/"

            image_url = TMDB_IMAGE_API + filename
            content, content_type = await fetch_image_with_proxy(image_url)
        except Exception as e:
            # TMDB image not found
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File not found: {filename}"
            )
        
        # Fetched TMDB image, cache it in minio
        await upload_to_minio(filename, content, content_type)

        stream, content_type = stream_from_minio(filename)
        return StreamingResponse(stream, media_type=content_type)

@router.post("/upload")
async def upload(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """
    Upload an image.
    """
    if not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be an image"
        )
    
    file_extension = file.filename.split('.')[-1] if '.' in file.filename else ''
    filename = f"{uuid.uuid4()}.{file_extension}" if file_extension else str(uuid.uuid4())
    
    content = await file.read()
    await upload_to_minio(filename, content, file.content_type)
    
    return {"filename": f"/{filename}"}
