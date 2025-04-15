from app.core.minio_client import minio_client
from app.core.config import settings
from fastapi import FastAPI
from contextlib import asynccontextmanager
import logging
from app.api.endpoints import images, movies, auth, collection, users
from app.db import engine
from app.models.movie import Base
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await init_minio()
    yield

app = FastAPI(lifespan=lifespan)

app.include_router(movies.router)
app.include_router(auth.router)
app.include_router(collection.router)
app.include_router(users.router)
app.include_router(images.router)

async def init_minio():
    # Initialize Minio bucket
    if not minio_client.bucket_exists(settings.MINIO_BUCKET_NAME):
        minio_client.make_bucket(settings.MINIO_BUCKET_NAME)
        policy = {
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Principal": "*",
                "Action": ["s3:GetObject"],
                "Resource": [f"arn:aws:s3:::{settings.MINIO_BUCKET_NAME}/*"]
            }]
        }
        minio_client.set_bucket_policy(settings.MINIO_BUCKET_NAME, json.dumps(policy))

async def init_db():
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=80, reload=True, log_level='trace')