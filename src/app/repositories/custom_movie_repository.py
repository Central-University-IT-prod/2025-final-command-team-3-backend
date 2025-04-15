from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.custom_movie import CustomMovie
import uuid

class CustomMovieRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_custom_movie(self, user_id: uuid.UUID, title: str, description: str, poster_path: str = None) -> CustomMovie:
        """
        Create a new custom movie.
        """
        custom_movie = CustomMovie(
            user_id=user_id,
            title=title,
            description=description,
            poster_path=poster_path
        )
        self.session.add(custom_movie)
        await self.session.commit()
        await self.session.refresh(custom_movie)
        return custom_movie

    async def get_custom_movie_by_id(
        self,
        custom_movie_id: uuid.UUID
    ) -> CustomMovie | None:
        """
        Retrieve a custom movie by its ID.
        """
        result = await self.session.execute(
            select(CustomMovie).where(CustomMovie.id == custom_movie_id)
        )
        return result.scalars().first()