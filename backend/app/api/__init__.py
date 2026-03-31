from fastapi import APIRouter
from app.api.endpoints import query_endpoint

api_router = APIRouter()
api_router.include_router(query_endpoint.router, prefix="/query", tags=["query"])