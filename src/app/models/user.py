from datetime import datetime, timezone

from sqlalchemy import Column, String, UniqueConstraint, DateTime, Boolean, Integer
from sqlalchemy.dialects.postgresql import UUID
from app.models.movie import Base
import uuid

class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint('email', name='unique_email'),
        UniqueConstraint('yandex_id', name='unique_yandex_id'),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(50), nullable=True)
    email = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=True)
    yandex_id = Column(Integer, nullable=True, unique=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.now(timezone.utc))
    profile_picture = Column(String(255), nullable=True)
    jwt_token = Column(String(255), nullable=True)
    is_admin = Column(Boolean, nullable=False, default=False)