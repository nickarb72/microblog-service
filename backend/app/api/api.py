from fastapi import APIRouter

from backend.app.api.endpoints import tweets, users

main_router = APIRouter()
main_router.include_router(users.router, tags=["users"])
main_router.include_router(tweets.router, tags=["tweets"])
