from collections import defaultdict
from app.repositories.movie_repository import MovieRepository
from app.repositories.user_movie_repository import UserMovieRepository
from app.services.movie_service import MovieService
from app.repositories.custom_movie_repository import CustomMovieRepository
from app.models.user_movie import UserMovie
from uuid import UUID
from typing import List, Optional, Dict
from fastapi import HTTPException, status
from app.schemas.enums import MovieStatus
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

class UserMovieService:
    def __init__(self, session: AsyncSession):
        self.user_movie_repo = UserMovieRepository(session)
        movie_repository = MovieRepository(session)
        self.movie_service = MovieService(movie_repository)
        self.custom_movie_repo = CustomMovieRepository(session)

    async def add_movie(
        self,
        user_id: UUID,
        movie_id: Optional[UUID] = None,
        custom_movie_id: Optional[UUID] = None,
        status: MovieStatus = MovieStatus.WILL_WATCH,
        rating: Optional[float] = None,
    ) -> UserMovie:
        """
        Add a movie or custom movie to the user's collection.
        """
        try:
            if movie_id:
                movie = await self.movie_service.get_movie_by_id(movie_id)
                if not movie:
                    raise ValueError("Movie not found")
            elif custom_movie_id:
                custom_movie = await self.custom_movie_repo.get_custom_movie_by_id(custom_movie_id)
                if not custom_movie:
                    raise ValueError("Custom movie not found")
            else:
                raise ValueError("Either movie_id or custom_movie_id must be provided")

            user_movie = await self.user_movie_repo.add_to_collection(
                user_id=user_id,
                movie_id=movie_id,
                custom_movie_id=custom_movie_id,
                status=status,
                rating=rating,
            )
            return user_movie

        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    async def update_status(
        self,
        user_id: UUID,
        user_movie_id: UUID,
        status: MovieStatus,
    ) -> UserMovie:
        """
        Update the status of a movie in the user's collection.
        """
        try:
            user_movie = await self.user_movie_repo.update_status(
                user_id=user_id,
                user_movie_id=user_movie_id,
                status=status,
            )
            return user_movie

        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    async def get_paginated(
        self,
        user_id: UUID,
        status: Optional[MovieStatus] = None,
        page: int = 1,
        page_size: int = 10,
    ) -> Dict:
        """
        Retrieve a paginated list of movies in the user's collection.
        Optionally filter by status.
        """
        try:
            if status:
                user_movies, total = await self.user_movie_repo.get_movies_by_status(
                    user_id=user_id,
                    status=status,
                    page=page,
                    page_size=page_size,
                )
            else:
                user_movies, total = await self.user_movie_repo.get_collection_paginated(
                    user_id=user_id,
                    page=page,
                    page_size=page_size,
                )

            return {
                "movies": user_movies,
                "total": total,
                "page": page,
                "page_size": page_size,
            }

        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    async def delete_from_collection(
        self,
        user_id: UUID,
        user_movie_id: UUID,
    ) -> None:
        """
        Remove a movie from the user's collection.
        """
        try:
            await self.user_movie_repo.delete_from_collection(
                user_id=user_id,
                user_movie_id=user_movie_id,
            )

        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    
    async def get_statuses_for_movies(self, user_id: UUID, movie_ids: list[UUID]) -> dict[UUID, str]:
        if not movie_ids:
            return {}
        stmt = select(UserMovie.movie_id, UserMovie.status).where(
            and_(
                UserMovie.user_id == user_id,
                UserMovie.movie_id.in_(movie_ids)
            )
        )
        result = await self.session.execute(stmt)
        return {row.movie_id: row.status for row in result.all()}
    
    async def get_statuses_for_movies(self, user_id: UUID, movie_ids: list[UUID]) -> dict[UUID, str]:
        return await self.user_movie_repo.get_statuses_for_movies(user_id, movie_ids)

    async def get_all(
        self,
        user_id: UUID,
        status: Optional[MovieStatus] = None
    ) -> List[UserMovie]:
        return await self.user_movie_repo.get_all_user_movies(user_id, status)
    
    async def compute_genre_relevancy(self, user_id: UUID) -> dict[int, float]:
        """Compute relevancy scores for each genre based on the user's collection."""
        user_movies = await self.get_all(user_id=user_id)
        R_g = defaultdict(float)
        default_rating = {
            MovieStatus.WATCHED: 7.0,    # Positive preference
            MovieStatus.WILL_WATCH: 5.0, # Neutral preference
            MovieStatus.DROPPED: 3.0     # Negative preference
        }
        for um in user_movies:
            if um.movie:  # Only movies with genres (skip CustomMovie)
                score = um.rating if um.rating is not None else default_rating[um.status]
                for genre_id in um.movie.genre_ids:
                    R_g[genre_id] += score
        return R_g
