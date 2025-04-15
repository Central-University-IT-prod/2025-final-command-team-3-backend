import asyncio
from datetime import date, datetime
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import aiohttp
from aiolimiter import AsyncLimiter
import random

from app.models.movie import Base, Movie

DATABASE_URL = "postgresql+asyncpg://postgres:password@prod-team-3-uad8jq68.REDACTED:8002/moviesdb"
API_KEY = 'REDACTED'
PROXIES = 'REDACTED'

engine = create_async_engine(DATABASE_URL)
async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
limiter = AsyncLimiter(40, 1)


async def fetch(session, url, params):
    retries = 5
    for attempt in range(retries):
        async with limiter:
            try:
                async with session.get(url, params=params, proxy=PROXIES) as response:
                    if response.status == 429:
                        wait = (2 ** attempt) + random.uniform(0, 1)
                        await asyncio.sleep(wait)
                        continue
                    response.raise_for_status()
                    return await response.json()
            except Exception as e:
                print(f"Ошибка запроса: {str(e)}")
                if attempt == retries - 1:
                    return None
                await asyncio.sleep(1)
    return None


async def process_page(db_session, movies_data):
    added = 0
    for movie_data in movies_data:
        if not movie_data.get('id'):
            continue

        try:
            existing = await db_session.execute(
                select(Movie).where(Movie.tmdb_id == movie_data['id'])
            )
            if existing.scalar():
                continue

            release_date = None
            if movie_data.get('release_date'):
                try:
                    release_date = date.fromisoformat(movie_data['release_date'])
                except ValueError:
                    pass

            movie = Movie(
                tmdb_id=movie_data['id'],
                adult=movie_data.get('adult', False),
                backdrop_path=movie_data.get('backdrop_path'),
                genre_ids=movie_data.get('genre_ids', []),
                original_language=movie_data.get('original_language', ''),
                original_title=movie_data.get('original_title', ''),
                overview=movie_data.get('overview', ''),
                popularity=movie_data.get('popularity', 0.0),
                poster_path=movie_data.get('poster_path'),
                release_date=release_date,
                title=movie_data.get('title', ''),
                video=movie_data.get('video', False),
                vote_average=movie_data.get('vote_average', 0.0),
                vote_count=movie_data.get('vote_count', 0),
            )
            db_session.add(movie)
            added += 1
        except Exception as e:
            print(f"Ошибка обработки фильма: {e}")

    try:
        await db_session.commit()
        return added
    except SQLAlchemyError as e:
        print(f"Ошибка базы данных: {e}")
        await db_session.rollback()
        return 0


async def parse_year(session, year):
    page = 1
    while True:
        params = {
            'api_key': API_KEY,
            'page': page,
            'language': 'ru-RU',
            # 'vote_count.gte': 1000.0,
            'sort_by': 'vote_average.desc',
            'primary_release_year': year
        }

        async with async_session() as db_session:
            data = await fetch(session, "https://api.themoviedb.org/3/discover/movie", params)
            if not data:
                break

            total_pages = min(data.get('total_pages', 1), 500)
            if page > total_pages:
                break

            movies = data.get('results', [])
            added = await process_page(db_session, movies)
            print(f"Год {year} | Страница {page}/{total_pages} | Добавлено: {added}")
            page += 1


async def main_loop():
    async with aiohttp.ClientSession() as http_session:
        while True:
            current_year = datetime.now().year
            for year in range(current_year, 1900 - 1, -1):
                print(f"Начинаем парсинг года: {year}")
                await parse_year(http_session, year)

            print("Цикл завершен. Повтор через 1 час...")
            await asyncio.sleep(3600)


async def main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    await main_loop()


if __name__ == "__main__":
    asyncio.run(main())