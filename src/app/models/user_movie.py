from sqlalchemy import Column, Enum, ForeignKey, Float, DateTime, UniqueConstraint, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
from app.models.movie import Base
from sqlalchemy.orm import relationship

class UserMovie(Base):
    __tablename__ = "user_movies"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    movie_id = Column(UUID(as_uuid=True), ForeignKey("movies.id"), nullable=True)
    custom_movie_id = Column(UUID(as_uuid=True), ForeignKey("custom_movies.id"), nullable=True)
    status = Column(Enum('will_watch', 'watched', 'dropped', name='status'), nullable=False, default='will_watch')
    rating = Column(Float, nullable=True)
    added_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    movie = relationship("Movie", back_populates="user_movies", lazy="selectin")
    custom_movie = relationship("CustomMovie", back_populates="user_movies", lazy="selectin")

    __table_args__ = (
        UniqueConstraint('user_id', 'movie_id', name='unique_user_movie'),
        UniqueConstraint('user_id', 'custom_movie_id', name='unique_user_custom_movie'),
        CheckConstraint('(movie_id IS NOT NULL AND custom_movie_id IS NULL) OR (movie_id IS NULL AND custom_movie_id IS NOT NULL)', name='check_movie_xor_custom'),
    )