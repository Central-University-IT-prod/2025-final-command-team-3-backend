from sqlalchemy import Column, String, Boolean, Float, Integer, ARRAY, Date, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import uuid

Base = declarative_base()


class Movie(Base):
    __tablename__ = "movies"
    __table_args__ = (
        UniqueConstraint('tmdb_id', name='unique_tmdb_id'),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    tmdb_id = Column(Integer, unique=True, nullable=False, index=True)

    adult = Column(Boolean, nullable=False)
    backdrop_path = Column(String(255), nullable=True)
    genre_ids = Column(ARRAY(Integer), nullable=False)
    original_language = Column(String(10), nullable=False)
    original_title = Column(String(255), nullable=False)
    overview = Column(String(2000), nullable=False)
    popularity = Column(Float, nullable=False)
    poster_path = Column(String(255), nullable=True)
    release_date = Column(Date, nullable=True)
    title = Column(String(255), nullable=False)
    video = Column(Boolean, nullable=False)
    vote_average = Column(Float, nullable=False)
    vote_count = Column(Integer, nullable=False)

    user_movies = relationship("UserMovie", back_populates="movie")