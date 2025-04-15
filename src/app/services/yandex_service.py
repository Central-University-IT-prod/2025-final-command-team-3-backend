import os

import httpx
from jose import jwt
from fastapi import HTTPException

class YandexAuthService:
    def __init__(self):
        pass

    @staticmethod
    async def get_yandex_jwt(oauth_token: str) -> str:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://login.yandex.ru/info",
                headers={"Authorization": f"OAuth {oauth_token}"},
                params={"format": "jwt"}
            )
            if response.status_code != 200:
                raise HTTPException(400, "Invalid OAuth token")
            return response.text

    def decode_yandex_jwt(self, token: str) -> dict:
        try:
            return jwt.decode(
                token,
                key=os.getenv("YANDEX_SECRET", "REDACTED"), # TODO ВРЕМЕННО ПОТОМ СДЕЛАТЬ ПО НОРМАЛЬНОМУ
                algorithms=["HS256"],
                options={"verify_aud": False}
            )
        except jwt.JWTError:
            raise HTTPException(401, "Invalid JWT")