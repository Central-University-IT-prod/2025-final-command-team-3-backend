from typing import Any, Coroutine, Sequence

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.movie import Movie
import uuid

class MovieRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_film_by_title(self, title: str) -> Movie | None:
        result = await self.session.execute(select(Movie).where(Movie.title == title))
        return result.scalars().first()

    async def get_movie_by_id(self, movie_id: uuid.UUID) -> Movie | None:
        result = await self.session.execute(select(Movie).where(Movie.id == movie_id))
        return result.scalars().first()

    async def get_top_movies(self, limit: int = 15) -> Sequence[Movie]:
        """Retrieve top movies by vote average with a minimum vote count."""
        result = await self.session.execute(
            select(Movie)
            .where(Movie.vote_count > 500)
            .order_by(Movie.vote_average.desc())
            .limit(limit)
        )
        return result.scalars().all()

    async def create_movie(self, movie_data: dict) -> Movie:
        movie = Movie(**movie_data)
        self.session.add(movie)
        await self.session.commit()
        await self.session.refresh(movie)
        return movie

    async def get_movies_by_ids(self, movie_ids: list[uuid.UUID]) -> list[Movie]:
        result = await self.session.execute(select(Movie).where(Movie.id.in_(movie_ids)))
        return result.scalars().all()
    
    async def get_all_movies(self) -> list[Movie]:
        """
        Fetch all movies from the database.
        """
        result = await self.session.execute(select(Movie))
        return result.scalars().all()