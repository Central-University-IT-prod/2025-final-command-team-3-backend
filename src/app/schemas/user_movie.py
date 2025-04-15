from typing import Optional
from app.schemas.enums import MovieStatus
from pydantic import UUID4, BaseModel
from datetime import datetime
from app.models.movie import Base

class UserMovieBase(BaseModel):
    user_id: UUID4
    movie_id: Optional[UUID4] = None
    custom_movie_id: Optional[UUID4] = None
    status: MovieStatus
    rating: Optional[float] = None
    added_at: datetime
    updated_at: Optional[datetime] = None

class UserMovieCreate(UserMovieBase):
    pass

class UserMovie(UserMovieBase):
    id: UUID4

    class Config:
        from_attributes = True