from app.models.user import User
from app.repositories.user_repository import UserRepository


class UserService:
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    async def register_user(self, username: str, email: str, hashed_password: str, access_token: str) -> User:
        user = User(username=username, email=email, hashed_password=hashed_password, jwt_token=access_token)
        return await self.user_repository.create_user(user)