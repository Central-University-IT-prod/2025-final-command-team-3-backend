import httpx
from jose import jwt
from app.core.config import settings

class GoogleOAuth:
    @staticmethod
    async def get_google_user_info(code: str):
        async with httpx.AsyncClient() as client:
            # Exchange code for tokens
            token_url = "https://oauth2.googleapis.com/token"
            token_data = {
                "code": code,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": settings.GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code"
            }
            
            token_response = await client.post(token_url, data=token_data)
            tokens = token_response.json()
            
            if 'id_token' not in tokens:
                return None

            # Get user info from ID token
            id_token = tokens['id_token']
            user_info = jwt.get_unverified_claims(id_token)
            
            return {
                "google_id": user_info['sub'],
                "email": user_info['email'],
                "name": user_info.get('name', user_info['email'].split('@')[0])
            }