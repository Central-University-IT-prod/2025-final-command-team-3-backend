import uuid
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.db import get_db
from app.main import app
from app.models.movie import Base
from app.core.security import create_access_token, pwd_context
from app.models.user import User
from app.models.movie import Movie
from unittest.mock import AsyncMock, patch
import pytest_asyncio
import os

TEST_DATABASE_URL = "postgresql+asyncpg://postgres:testpass@db:5432/testdb"
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
test_async_session = sessionmaker(test_engine, expire_on_commit=False, class_=AsyncSession)

@pytest_asyncio.fixture(scope="session")
async def setup_database():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest_asyncio.fixture
async def db_session(setup_database):
    async with test_async_session() as session:
        yield session
        await session.rollback()

@pytest_asyncio.fixture
def override_get_db(db_session):
    async def _override_get_db():
        yield db_session
    return _override_get_db

@pytest_asyncio.fixture
async def client(override_get_db):
    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()

@pytest_asyncio.fixture
async def test_user(db_session):
    user = User(
        email="test@example.com",
        username="testuser",
        hashed_password=pwd_context.hash("TestPass1!"),
        is_admin=False
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    token = create_access_token({"sub": user.email})
    return user, token

@pytest_asyncio.fixture
async def admin_user(db_session):
    admin = User(
        email="admin@example.com",
        username="admin",
        hashed_password=pwd_context.hash("AdminPass1!"),
        is_admin=True
    )
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)
    token = create_access_token({"sub": admin.email})
    return admin, token

@pytest_asyncio.fixture
async def test_movies(db_session):
    movies = [
        Movie(
            id=uuid.uuid4(),
            tmdb_id=1,
            title="Movie 1",
            overview="Overview 1",
            genre_ids=[28, 12],
            original_language="en",
            original_title="Movie 1",
            adult=False,
            backdrop_path="/backdrop1.jpg",
            popularity=10.0,
            poster_path="/poster1.jpg",
            release_date="2020-01-01",
            video=False,
            vote_average=7.5,
            vote_count=1000
        ),
        Movie(
            id=uuid.uuid4(),
            tmdb_id=2,
            title="Movie 2",
            overview="Overview 2",
            genre_ids=[35, 18],
            original_language="en",
            original_title="Movie 2",
            adult=False,
            backdrop_path="/backdrop2.jpg",
            popularity=8.0,
            poster_path="/poster2.jpg",
            release_date="2021-01-01",
            video=False,
            vote_average=8.0,
            vote_count=1500
        ),
    ]
    db_session.add_all(movies)
    await db_session.commit()
    return movies

@pytest_asyncio.fixture
def mock_minio_client():
    with patch('app.core.minio_client.minio_client', new_callable=AsyncMock) as mock:
        mock.bucket_exists.return_value = True
        mock.stat_object.return_value = True
        mock.put_object.return_value = None
        yield mock

@pytest_asyncio.fixture
def mock_es():
    with patch('app.core.elasticsearch.AsyncElasticsearch', new_callable=AsyncMock) as mock:
        yield mock