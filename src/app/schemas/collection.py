from app.schemas.enums import MovieStatus
from app.schemas.movie import MovieResponse
from pydantic import BaseModel, UUID4, Field, model_validator
from datetime import datetime
from typing import Optional
from enum import Enum

class AddToCollectionRequest(BaseModel):
    movie_id: Optional[UUID4] = None
    title: Optional[str] = None
    description: Optional[str] = None
    # Filename returned from /upload
    poster_path: Optional[str] = None
    status: Optional[MovieStatus] = MovieStatus.WILL_WATCH

    @model_validator(mode='after')
    def check_exclusive_fields(self):
        if self.movie_id and (self.title or self.description or self.poster_path):
            raise ValueError("Cannot provide both movie_id and custom movie details")
        if not self.movie_id and not self.title:
            raise ValueError("Either movie_id or title must be provided")
        return self

class CollectionMovieResponse(MovieResponse):
    added_at: datetime
    rating: Optional[float] = None