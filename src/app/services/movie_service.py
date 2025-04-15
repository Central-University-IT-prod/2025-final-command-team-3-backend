from typing import Any, Coroutine, Sequence

from app.repositories.movie_repository import MovieRepository
from app.models.movie import Movie
import uuid

class MovieService:
    def __init__(self, movie_repository: MovieRepository):
        self.movie_repository = movie_repository

    async def get_movie_by_title(self, title: str) -> Movie | None:
        return await self.movie_repository.get_film_by_title(title)

    async def get_movie_by_id(self, movie_id: uuid.UUID) -> Movie | None:
        return await self.movie_repository.get_movie_by_id(movie_id)

    async def get_top_movies(self, limit: int = 15) -> Sequence[Movie]:
        """Fetch top movies with a configurable limit."""
        return await self.movie_repository.get_top_movies(limit=limit)

    async def create_manual_movie(self, title: str, description: str) -> Movie:
        movie_data = {
            'title': title,
            'overview': description,
            'tmdb_id': None,
            'adult': False,
            'genre_ids': [],
            'original_language': 'en',
            'original_title': title,
            'popularity': 0.0,
            'video': False,
            'vote_average': 0.0,
            'vote_count': 0,
            'backdrop_path': None,
            'poster_path': None,
            'release_date': None,
        }
        return await self.movie_repository.create_movie(movie_data)