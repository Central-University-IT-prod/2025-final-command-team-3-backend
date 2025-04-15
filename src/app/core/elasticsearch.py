from elasticsearch import AsyncElasticsearch
from fastapi import Depends

async def get_es():
    es = AsyncElasticsearch("http://elasticsearch:9200")
    try:
        yield es
    finally:
        await es.close()
