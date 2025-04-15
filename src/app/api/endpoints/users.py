from fastapi import Depends
from fastapi.routing import APIRouter

from app.core.security import get_current_user
from app.schemas.user import User

router = APIRouter(prefix="/api/user", tags=["users"])

@router.get("/me", response_model=User)
async def get_user_info(current_user: User = Depends(get_current_user)):
    return current_user