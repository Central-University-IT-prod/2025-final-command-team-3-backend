from typing import Optional
from app.repositories.movie_repository import MovieRepository
from app.schemas.enums import MovieStatus
from app.schemas.movie import MovieResponse, get_genre_names
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import get_db
from app.services.user_movie_service import UserMovieService
from app.services.movie_service import MovieService
from app.services.custom_movie_service import CustomMovieService
from app.core.security import get_current_user
from app.schemas.user import User
from app.schemas.collection import AddToCollectionRequest, CollectionMovieResponse
import uuid

router = APIRouter(prefix="/api/collection", tags=["collection"])

# Service dependencies
async def get_user_movie_service(db: AsyncSession = Depends(get_db)):
    return UserMovieService(db)

async def get_movie_service(db: AsyncSession = Depends(get_db)):
    movie_repository = MovieRepository(db)
    return MovieService(movie_repository)

async def get_custom_movie_service(db: AsyncSession = Depends(get_db)):
    return CustomMovieService(db)

@router.post("/add", response_model=CollectionMovieResponse)
async def add_to_collection(
    request_data: AddToCollectionRequest,
    user_movie_service: UserMovieService = Depends(get_user_movie_service),
    movie_service: MovieService = Depends(get_movie_service),
    custom_movie_service: CustomMovieService = Depends(get_custom_movie_service),
    current_user: User = Depends(get_current_user),
):
    """
    Add a movie or custom movie to the user's collection.
    """
    try:
        if request_data.movie_id:
            # Add a TMDB movie to the collection
            movie = await movie_service.get_movie_by_id(request_data.movie_id)
            if not movie:
                raise HTTPException(status_code=404, detail="Movie not found")

            user_movie = await user_movie_service.add_movie(
                user_id=current_user.id,
                movie_id=request_data.movie_id,
                status=request_data.status if request_data.status else MovieStatus.WILL_WATCH,
            )
            return CollectionMovieResponse(
                id=user_movie.id,
                title=movie.title,
                description=movie.overview,
                status=user_movie.status,
                added_at=user_movie.added_at,
                rating=user_movie.rating,
                poster_path=movie.poster_path,
                genres=get_genre_names(movie.genre_ids),
                backdrop_path=movie.backdrop_path,
                release_date=movie.release_date,
            )
        else:
            # Add a custom movie to the collection
            if not request_data.title:
                raise HTTPException(status_code=400, detail="Title is required for custom movies")

            custom_movie = await custom_movie_service.create_custom_movie(
                user_id=current_user.id,
                title=request_data.title,
                description=request_data.description,
                poster_path=request_data.poster_path,
            )
            user_movie = await user_movie_service.add_movie(
                user_id=current_user.id,
                custom_movie_id=custom_movie.id,
                status=request_data.status if request_data.status else MovieStatus.WILL_WATCH,
            )
            return CollectionMovieResponse(
                id=user_movie.id,
                title=custom_movie.title,
                description=custom_movie.description,
                status=user_movie.status,
                added_at=user_movie.added_at,
                rating=user_movie.rating,
                poster_path=custom_movie.poster_path
            )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{movie_identifier}/{status}", response_model=CollectionMovieResponse)
async def update_status(
    movie_identifier: uuid.UUID,
    status: MovieStatus,
    user_movie_service: UserMovieService = Depends(get_user_movie_service),
    current_user: User = Depends(get_current_user),
):
    """
    Update the status of a movie in the user's collection using its UUID (Movie.id or CustomMovie.id).
    """
    # Find the UserMovie entry by user_id and movie_identifier
    user_movie = await user_movie_service.user_movie_repo.get_by_user_and_movie_identifier(
        user_id=current_user.id,
        movie_identifier=movie_identifier
    )
    if not user_movie:
        raise HTTPException(status_code=404, detail="Movie not found in your collection")

    # Update the status
    try:
        updated_user_movie = await user_movie_service.update_status(
            user_id=current_user.id,
            user_movie_id=user_movie.id,
            status=status,
        )

        # Determine the title and description based on whether it's a TMDB movie or a custom movie
        if updated_user_movie.movie:
            title = updated_user_movie.movie.title
            description = updated_user_movie.movie.overview
            poster_path = updated_user_movie.movie.poster_path
            genres = get_genre_names(updated_user_movie.movie.genre_ids)
            backdrop_path = updated_user_movie.movie.backdrop_path
            release_date = updated_user_movie.movie.release_date
        elif updated_user_movie.custom_movie:
            title = updated_user_movie.custom_movie.title
            description = updated_user_movie.custom_movie.description
            poster_path = updated_user_movie.custom_movie.poster_path
            genres = []  # Custom movies may not have genres
            backdrop_path = None
            release_date = None
        else:
            raise HTTPException(status_code=500, detail="Invalid user movie data")

        return CollectionMovieResponse(
            id=updated_user_movie.id,
            title=title,
            description=description,
            status=updated_user_movie.status,
            added_at=updated_user_movie.added_at,
            rating=updated_user_movie.rating,
            poster_path=poster_path,
            genres=genres,
            backdrop_path=backdrop_path,
            release_date=release_date,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/", response_model=list[CollectionMovieResponse])
async def get_collection(
    status: Optional[MovieStatus] = None,
    user_movie_service: UserMovieService = Depends(get_user_movie_service),
    current_user: User = Depends(get_current_user),
):
    try:
        user_movies = await user_movie_service.get_all(user_id=current_user.id, status=status)
        movies = []
        for user_movie in user_movies:
            if user_movie.movie:
                movie = user_movie.movie
                movie_response = MovieResponse(
                    id=movie.id,
                    tmdb_id=movie.tmdb_id,
                    adult=movie.adult,
                    backdrop_path=movie.backdrop_path,
                    original_language=movie.original_language,
                    original_title=movie.original_title,
                    overview=movie.overview,
                    popularity=movie.popularity,
                    poster_path=movie.poster_path,
                    release_date=movie.release_date,
                    title=movie.title,
                    video=movie.video,
                    vote_average=movie.vote_average,
                    vote_count=movie.vote_count,
                    genres=get_genre_names(movie.genre_ids),
                    status=user_movie.status
                )
            elif user_movie.custom_movie:
                custom_movie = user_movie.custom_movie
                movie_response = MovieResponse(
                    id=custom_movie.id,
                    title=custom_movie.title,
                    overview=custom_movie.description,
                    status=user_movie.status,
                    poster_path=custom_movie.poster_path,
                )
            else:
                continue

            collection_movie = CollectionMovieResponse(
                **movie_response.model_dump(),
                added_at=user_movie.added_at,
                rating=user_movie.rating
            )
            movies.append(collection_movie)
        return movies
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{movie_identifier}", status_code=204)
async def delete_from_collection(
    movie_identifier: uuid.UUID,
    user_movie_service: UserMovieService = Depends(get_user_movie_service),
    current_user: User = Depends(get_current_user),
):
    """
    Remove a movie from the user's collection using its UUID (Movie.id or CustomMovie.id).
    """
    # Find the UserMovie entry by user_id and movie_identifier
    user_movie = await user_movie_service.user_movie_repo.get_by_user_and_movie_identifier(
        user_id=current_user.id,
        movie_identifier=movie_identifier
    )
    if not user_movie:
        raise HTTPException(status_code=404, detail="Movie not found in your collection")

    # Delete the entry
    try:
        await user_movie_service.delete_from_collection(
            user_id=current_user.id,
            user_movie_id=user_movie.id,
        )
        return None  # No content for DELETE
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))