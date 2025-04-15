from typing import Optional
from app.api.endpoints.collection import get_movie_service, get_user_movie_service
from app.api.endpoints.images import fetch_image_with_proxy, upload_from_url
from app.services.user_movie_service import UserMovieService
from elasticsearch import AsyncElasticsearch
from fastapi import APIRouter, Depends, HTTPException, Query, status
from httpx import AsyncClient
from pydantic import HttpUrl
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import get_current_user
from app.core.elasticsearch import get_es
from app.db import get_db
from app.models.user import User
from app.repositories.movie_repository import MovieRepository
from app.schemas.movie import MetadataResponse, MovieResponse, get_genre_names, genre_names
from app.services.movie_service import MovieService
from bs4 import BeautifulSoup
import uuid

router = APIRouter(prefix="/api/movies", tags=["movies"])

@router.get("/search", response_model=list[MovieResponse])
async def search_movies_fts(
    title: Optional[str] = Query(None, description="Title to search for"),
    genres: Optional[str] = Query(None, description="Comma-separated list of genres to filter by"),
    min_rating: Optional[float] = Query(None, ge=0, le=10, description="Minimum rating to filter by"),
    db: AsyncSession = Depends(get_db),
    es: AsyncElasticsearch = Depends(get_es),
    current_user: User = Depends(get_current_user),
    user_movie_service: UserMovieService = Depends(get_user_movie_service),
):
    if (title is None or title == "") and (genres is None or genres == "") and min_rating is None:
        return []

    # Process genres into a list
    genre_list = genres.split(',') if genres else []

    # Normalize & validate genres
    genre_list = [genre.strip().lower() for genre in genre_list]
    for genre in genre_list:
        if genre not in genre_names:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid genre: {genre} (valid genres: {', '.join(genre_names)})"
            )

    # Build filter clauses
    filter_clauses = []
    if genre_list:
        filter_clauses.append({"terms": {"genres": genre_list}})
    if min_rating is not None:
        filter_clauses.append({"range": {"vote_average": {"gte": min_rating}}})

    # Construct Elasticsearch query with filters
    search_body = {
        "query": {
            "bool": {
                "must": [
                    {
                        "multi_match": {
                            "query": title,
                            "fields": ["title", "overview", "genres"],
                            "fuzziness": "AUTO"
                        }
                    }
                ],
                "filter": filter_clauses
            }
        }
    }

    # Execute the search
    response = await es.search(index="movies", body=search_body)
    hits = response['hits']['hits']

    # Fetch movie details from the database
    movie_ids = [uuid.UUID(hit['_id']) for hit in hits]
    movie_repository = MovieRepository(db)
    movies = await movie_repository.get_movies_by_ids(movie_ids)

    # Preserve order and format response
    movies_dict = {movie.id: movie for movie in movies}
    ordered_movies = [movies_dict[movie_id] for movie_id in movie_ids if movie_id in movies_dict]

    movie_ids = [mov.id for mov in ordered_movies]
    statuses = await user_movie_service.get_statuses_for_movies(current_user.id, movie_ids)

    return [
        MovieResponse(
            **mov.__dict__,
            genres=get_genre_names(mov.genre_ids),
            status=statuses.get(mov.id, None)
        )
        for mov in ordered_movies
    ]

@router.get("/top", response_model=list[MovieResponse])
async def get_top_movies(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    user_movie_service: UserMovieService = Depends(get_user_movie_service),
):
    movie_repository = MovieRepository(db)
    movie_service = MovieService(movie_repository)
    movies = await movie_service.get_top_movies()

    movie_ids = [mov.id for mov in movies]
    statuses = await user_movie_service.get_statuses_for_movies(current_user.id, movie_ids)

    return [
        MovieResponse(
            **mov.__dict__,
            genres=get_genre_names(mov.genre_ids),
            status=statuses.get(mov.id, None)
        )
        for mov in movies
    ]

@router.get("/recommended", response_model=list[MovieResponse])
async def get_recommended_movies(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    user_movie_service: UserMovieService = Depends(get_user_movie_service),
    movie_service: MovieService = Depends(get_movie_service),
):
    """Return personalized movies sorted by relevancy and vote average."""
    # Compute genre relevancy scores
    R_g = await user_movie_service.compute_genre_relevancy(current_user.id)
    
    # Get top 100 candidate movies by vote average
    candidates = await movie_service.get_top_movies(limit=300)
    
    # Compute final scores: vote_average + relevancy_score
    final_scores = [
        (
            candidate,
            sum(R_g.get(g, 0) for g in candidate.genre_ids),  # Relevancy score
            candidate.vote_average                            # Vote average
        )
        for candidate in candidates
    ]
    
    # Sort by combined score (vote_average + relevancy_score) and take top 100
    sorted_candidates = sorted(final_scores, key=lambda x: x[2] + x[1], reverse=True)[:100]
    movies = [x[0] for x in sorted_candidates]
    
    # Fetch statuses for the returned movies
    movie_ids = [mov.id for mov in movies]
    statuses = await user_movie_service.get_statuses_for_movies(current_user.id, movie_ids)
    
    # Construct response
    return [
        MovieResponse(
            **mov.__dict__,
            genres=get_genre_names(mov.genre_ids),
            status=statuses.get(mov.id, None)
        )
        for mov in movies
        if statuses.get(mov.id, None) is None
    ]

@router.post("/reindex", status_code=status.HTTP_200_OK)
async def reindex_movies(
    db: AsyncSession = Depends(get_db),
    es: AsyncElasticsearch = Depends(get_es),
    current_user: User = Depends(get_current_user)
):
    """
    Reset Elasticsearch index and reindex all movies from the database.
    Restricted to admin users.
    """

    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin users can reindex movies"
        )

    try:
        # Delete existing index if it exists
        if await es.indices.exists(index="movies"):
            await es.indices.delete(index="movies")

        # Create new index with mappings
        await es.indices.create(index="movies", body={
            "mappings": {
                "properties": {
                    "title": {"type": "text"},
                    "overview": {"type": "text"},
                    "release_date": {"type": "date"},
                    "genres": {"type": "keyword"},
                    "vote_average": {"type": "float"}
                }
            }
        })

        # Fetch all movies from the database
        movie_repository = MovieRepository(db)
        movies = await movie_repository.get_all_movies()

        if not movies:
            return {"message": "No movies found in the database to index"}

        # Prepare bulk indexing actions
        actions = [
            {
                "_index": "movies",
                "_id": str(movie.id),
                "_source": {
                    "title": movie.title,
                    "overview": movie.overview,
                    "release_date": movie.release_date.isoformat() if movie.release_date else None,
                    "genres": get_genre_names(movie.genre_ids),
                    "vote_average": movie.vote_average
                }
            }
            for movie in movies
        ]

        # Perform bulk indexing
        from elasticsearch.helpers import async_bulk
        successes, errors = await async_bulk(es, actions)

        if errors:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to index some movies: {errors}"
            )

        return {
            "message": f"Successfully reindexed {successes} movies",
            "total_movies": len(movies)
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error reindexing movies: {str(e)}"
        )

@router.get("/extract-metadata", response_model=MetadataResponse)
async def extract_metadata(
    url: HttpUrl = Query(..., description="The URL to extract metadata from")
):
    """
    Extract title, description, and image URL from the given website URL.
    Looks for Open Graph meta tags (og:title, og:description, og:image).
    If not found, falls back to standard title and description tags.
    """
    # Fetch the webpage content
    async with AsyncClient() as client:
        try:
            response = await client.get(str(url), timeout=10.0, follow_redirects=True)
            response.raise_for_status()
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to fetch URL: {str(e)}"
            )

    # Parse the HTML content
    html = response.text
    soup = BeautifulSoup(html, 'html.parser')

    # Extract title (Open Graph first, then fallback to <title>)
    title_tag = soup.find('meta', property='og:title')
    if not title_tag:
        title_tag = soup.find('title')
    title = (
        title_tag['content'] if title_tag and 'content' in title_tag.attrs
        else title_tag.text if title_tag else None
    )

    # Extract description (Open Graph first, then fallback to meta name="description")
    description_tag = soup.find('meta', property='og:description')
    if not description_tag:
        description_tag = soup.find('meta', {'name': 'description'})
    description = description_tag['content'] if description_tag else None

    # Extract image (Open Graph only)
    image_tag = soup.find('meta', property='og:image')
    image_url = str(image_tag['content']) if image_tag else None
    our_image_filename = await upload_from_url(image_url)

    return MetadataResponse(
        title=title,
        overview=description,
        poster_url=our_image_filename
    )
