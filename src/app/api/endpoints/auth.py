from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

import logging
from app.core.security import (
    authenticate_user,
    create_access_token,
    pwd_context,
    is_strong_password
)
from app.db import get_db
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserCreate, Token, UserLogin, YandexAuthRequest
from app.services.user_service import UserService
from app.services.yandex_service import YandexAuthService

router = APIRouter(prefix="/api/auth", tags=["auth"])
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

@router.post("/register", response_model=Token)
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    user_repo = UserRepository(db)
    user_service = UserService(user_repo)

    user = await user_repo.get_user_by_email(str(user_data.email))
    if user:
        if user.yandex_id is not None or user.hashed_password is None:
            raise HTTPException(
                status_code=400,
                detail="Используйте вход через Яндекс"
            )
        raise HTTPException(
            status_code=400,
            detail="Email already exists"
        )

    if not is_strong_password(user_data.password):
        raise HTTPException(
            status_code=400,
            detail="Password not strong enough (need >=8 characters, >=1 numbers, >=1 letters, >=1 special characters)"
        )
    
    hashed_password = pwd_context.hash(user_data.password)
    username = user_data.username or str(user_data.email).split("@")[0]

    access_token = create_access_token(
        data={"sub": user_data.email}
    )

    await user_service.register_user(
        username,
        str(user_data.email),
        hashed_password,
        access_token
    )

    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/login", response_model=Token)
async def login(
    form_data: UserLogin,
    db: AsyncSession = Depends(get_db)
):
    user = await authenticate_user(db, form_data.email, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return {"access_token": user.jwt_token, "token_type": "bearer"}


async def get_yandex_service() -> YandexAuthService:
    return YandexAuthService()

async def get_user_repo(db: AsyncSession = Depends(get_db)) -> UserRepository:
    return UserRepository(db)

@router.post("/yandex", response_model=Token)
async def yandex_auth(
    request: YandexAuthRequest,
    yandex_service: YandexAuthService = Depends(get_yandex_service),
    repo: UserRepository = Depends(get_user_repo)
):
    yandex_jwt = await yandex_service.get_yandex_jwt(request.token)
    payload = yandex_service.decode_yandex_jwt(yandex_jwt)
    if not payload:
        logger.error("Неверный токен Яндекс")
        raise HTTPException(status_code=400, detail="Invalid token")

    yandex_id = payload["uid"]
    email = payload["email"]
    yandex_picture_url = "https://avatars.yandex.net/get-yapic/" + payload["avatar_id"]

    user = await repo.get_by_yandex_id(yandex_id)
    if user:
        # Обновляем токен для существующего пользователя
        access_token = create_access_token(data={"sub": email})
        user.jwt_token = access_token
        await repo.update_user(user)
        logger.info(f"Обновлен токен для пользователя Яндекс: {email}")
    else:
        # Если пользователь не найден, проверяем, существует ли пользователь с таким email
        existing_user = await repo.get_user_by_email(email)
        if existing_user:
            if existing_user.yandex_id:
                logger.warning(f"Попытка привязки уже привязанного аккаунта Яндекс для email: {email}")
                raise HTTPException(
                    status_code=409,
                    detail="Yandex account already linked"
                )
            # Привязываем Yandex ID к существующему пользователю
            access_token = create_access_token(data={"sub": email})
            existing_user.jwt_token = access_token
            existing_user.yandex_id = yandex_id
            await repo.update_user(existing_user)
            logger.info(f"Привязан аккаунт Яндекс к существующему пользователю: {email}")
        else:
            # Создаем нового пользователя
            username = email.split("@")[0]
            access_token = create_access_token(data={"sub": email})
            user = User(
                email=str(email),
                yandex_id=yandex_id,
                username=username,
                jwt_token=access_token,
                profile_picture=yandex_picture_url
            )
            await repo.create_user(user)
            logger.info(f"Создан новый пользователь через Яндекс: {email}")

    return {"access_token": access_token, "token_type": "bearer"}