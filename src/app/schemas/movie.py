from datetime import date
from typing import List, Optional
from app.schemas.enums import MovieStatus
from pydantic import BaseModel, UUID4

genre_mapping = {
    28: "боевик",
    12: "приключения",
    16: "мультфильм",
    35: "комедия",
    80: "криминал",
    99: "документальный",
    18: "драма",
    10751: "семейный",
    14: "фэнтези",
    36: "история",
    27: "ужасы",
    10402: "музыка",
    9648: "детектив",
    10749: "мелодрама",
    878: "фантастика",
    10770: "телевизионный фильм",
    53: "триллер",
    10752: "военный",
    37: "вестерн"
}

genre_names = list(genre_mapping.values())

def get_genre_names(genre_ids: list[int]) -> list[str]:
    return [genre_mapping[gid] for gid in genre_ids if gid in genre_mapping]

class MovieBase(BaseModel):
    tmdb_id: int
    adult: bool
    backdrop_path: Optional[str] = None
    genre_ids: List[int]
    original_language: str
    original_title: str
    overview: str
    popularity: float
    poster_path: Optional[str] = None
    release_date: Optional[date] = None
    title: str
    video: bool
    vote_average: float
    vote_count: int


class MovieCreate(MovieBase):
    pass


class Movie(MovieBase):
    id: UUID4

    class Config:
        from_attributes = True


class MovieResponse(BaseModel):
    id: UUID4
    tmdb_id: Optional[int] = None
    adult: Optional[bool] = None
    backdrop_path: Optional[str] = None
    original_language: Optional[str] = None
    original_title: Optional[str] = None
    overview: Optional[str] = None
    popularity: Optional[float] = None
    poster_path: Optional[str] = None
    release_date: Optional[date] = None
    title: str
    video: Optional[bool] = None
    vote_average: Optional[float] = None
    vote_count: Optional[int] = None
    genres: Optional[List[str]] = None
    status: Optional[MovieStatus] = None

    class Config:
        from_attributes = True

class MetadataResponse(BaseModel):
    title: Optional[str]
    overview: Optional[str]
    poster_url: Optional[str]
