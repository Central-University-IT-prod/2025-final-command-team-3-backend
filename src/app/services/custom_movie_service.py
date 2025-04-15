from typing import Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.custom_movie import CustomMovie
from app.repositories.custom_movie_repository import CustomMovieRepository
from fastapi import HTTPException, status

class CustomMovieService:
    def __init__(self, session: AsyncSession):
        self.custom_movie_repo = CustomMovieRepository(session)

    async def create_custom_movie(
        self,
        user_id: UUID,
        title: str,
        description: Optional[str] = None,
        poster_path: Optional[str] = None
    ) -> CustomMovie:
        """
        Create a new custom movie for a user.
        """
        try:
            custom_movie = await self.custom_movie_repo.create_custom_movie(
                user_id=user_id,
                title=title,
                description=description,
                poster_path=poster_path
            )
            return custom_movie
            
        except Exception as e:
            if "unique_user_custom_movie" in str(e):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="A custom movie with this title already exists in your collection"
                )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create custom movie"
            )

    async def get_custom_movie(
        self,
        user_id: UUID,
        custom_movie_id: UUID
    ) -> CustomMovie:
        """
        Retrieve a specific custom movie by ID.
        """
        custom_movie = await self.custom_movie_repo.get_custom_movie_by_id(custom_movie_id)
        if not custom_movie or custom_movie.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Custom movie not found"
            )
        return custom_movie