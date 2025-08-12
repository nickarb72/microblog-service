from fastapi import APIRouter
from .endpoints import users, tweets

main_router = APIRouter()
# main_router.include_router(users.router)
main_router.include_router(tweets.router, tags=["tweets"])
