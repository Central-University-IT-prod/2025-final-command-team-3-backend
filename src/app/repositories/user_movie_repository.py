import uuid
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from sqlalchemy import or_, select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_movie import UserMovie
from app.schemas.enums import MovieStatus


class UserMovieRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add_to_collection(
        self,
        user_id: uuid.UUID,
        movie_id: uuid.UUID = None,
        custom_movie_id: uuid.UUID = None,
        status: MovieStatus = MovieStatus.WILL_WATCH,
        rating: float = None
    ) -> UserMovie:
        """
        Add a movie or custom movie to the user's collection.
        """
        if not (movie_id or custom_movie_id):
            raise ValueError("Either movie_id or custom_movie_id must be provided")
        
        # Check for existing entry using proper NULL handling
        existing_query = select(UserMovie).where(
            and_(
                UserMovie.user_id == user_id,
                or_(
                    and_(UserMovie.movie_id == movie_id, movie_id is not None),
                    and_(UserMovie.custom_movie_id == custom_movie_id, custom_movie_id is not None)
                )
            )
        )

        existing = await self.session.execute(existing_query)
        first = existing.scalars().first()
        if first:
            raise ValueError("Movie already in collection")

        user_movie = UserMovie(
            user_id=user_id,
            movie_id=movie_id,
            custom_movie_id=custom_movie_id,
            status=status,
            rating=rating
        )
        self.session.add(user_movie)
        
        try:
            await self.session.commit()
        except Exception as e:
            await self.session.rollback()
            if "unique_user_movie" in str(e).lower() or "unique_user_custom_movie" in str(e).lower():
                raise ValueError("Movie already in collection")
            raise
        
        await self.session.refresh(user_movie)
        return user_movie

    async def update_status(
        self,
        user_id: uuid.UUID,
        user_movie_id: uuid.UUID,
        status: MovieStatus,
    ) -> UserMovie:
        """
        Update the status and rating of a movie in the user's collection.
        """
        result = await self.session.execute(
            select(UserMovie).where(
                and_(
                    UserMovie.user_id == user_id,
                    UserMovie.id == user_movie_id
                )
            )
        )
        user_movie = result.scalars().first()
        if not user_movie:
            raise ValueError("Movie not found in collection")

        user_movie.status = status
        user_movie.updated_at = datetime.now(timezone.utc)
        await self.session.commit()
        await self.session.refresh(user_movie)
        return user_movie

    async def get_collection_paginated(
        self,
        user_id: uuid.UUID,
        page: int,
        page_size: int
    ) -> Tuple[List[UserMovie], int]:
        """
        Retrieve a paginated list of movies in the user's collection (will_watch + watched + dropped).
        """
        offset = (page - 1) * page_size
        result = await self.session.execute(
            select(UserMovie)
            .where(UserMovie.user_id == user_id)
            .offset(offset)
            .limit(page_size)
        )
        movies = result.scalars().all()

        total = await self.session.execute(
            select(func.count(UserMovie.id))
            .where(UserMovie.user_id == user_id)
        )
        total_count = total.scalar()

        return movies, total_count

    async def get_movies_by_status(
        self,
        user_id: uuid.UUID,
        status: MovieStatus,
        page: int,
        page_size: int
    ) -> Tuple[List[UserMovie], int]:
        """
        Retrieve a paginated list of movies in the user's collection by status.
        """
        offset = (page - 1) * page_size
        result = await self.session.execute(
            select(UserMovie)
            .where(
                and_(
                    UserMovie.user_id == user_id,
                    UserMovie.status == status
                )
            )
            .offset(offset)
            .limit(page_size)
        )
        movies = result.scalars().all()

        total = await self.session.execute(
            select(func.count(UserMovie.id))
            .where(
                and_(
                    UserMovie.user_id == user_id,
                    UserMovie.status == status
                )
            )
        )
        total_count = total.scalar()

        return movies, total_count

    async def get_movie_details(
        self,
        user_id: uuid.UUID,
        movie_id: uuid.UUID
    ) -> UserMovie:
        """
        Retrieve details of a specific movie in the user's collection.
        """
        result = await self.session.execute(
            select(UserMovie)
            .where(
                and_(
                    UserMovie.user_id == user_id,
                    UserMovie.movie_id == movie_id
                )
            )
        )
        user_movie = result.scalars().first()
        if not user_movie:
            raise ValueError("Movie not found in collection")
        return user_movie

    async def delete_from_collection(
        self,
        user_id: uuid.UUID,
        user_movie_id: uuid.UUID
    ) -> None:
        """
        Remove a movie from the user's collection.
        """
        result = await self.session.execute(
            select(UserMovie)
            .where(
                and_(
                    UserMovie.user_id == user_id,
                    UserMovie.id == user_movie_id
                )
            )
        )
        user_movie = result.scalars().first()
        if not user_movie:
            raise ValueError("Movie not found in collection")

        await self.session.delete(user_movie)
        await self.session.commit()
    
    async def get_statuses_for_movies(self, user_id: uuid.UUID, movie_ids: list[uuid.UUID]) -> dict[uuid.UUID, str]:
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

    async def get_all_user_movies(
        self,
        user_id: uuid.UUID,
        status: Optional[MovieStatus] = None
    ) -> List[UserMovie]:
        query = select(UserMovie).where(UserMovie.user_id == user_id)
        if status:
            query = query.where(UserMovie.status == status)
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def get_by_user_and_movie_identifier(
        self,
        user_id: uuid.UUID,
        movie_identifier: uuid.UUID
    ) -> UserMovie | None:
        """
        Retrieve a UserMovie entry by user_id and a movie_identifier that matches either movie_id or custom_movie_id.
        """
        result = await self.session.execute(
            select(UserMovie).where(
                and_(
                    UserMovie.user_id == user_id,
                    or_(
                        UserMovie.movie_id == movie_identifier,
                        UserMovie.custom_movie_id == movie_identifier
                    )
                )
            )
        )
        return result.scalars().first()