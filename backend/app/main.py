from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from backend.app.api.api import main_router
from backend.app.db.session import engine
from backend.scripts.fill_db import init_db_with_test_data

PORT = 8000


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db_with_test_data()

    yield

    await engine.dispose()


app = FastAPI(
    title="Microblog API",
    description="API for microblogging service",
    version="1.0.0",
    lifespan=lifespan,
    openapi_tags=[
        {"name": "tweets", "description": "Operations with tweets"},
        {
            "name": "users",
            "description": "Operations with users",
        },
    ],
)

app.include_router(main_router, prefix="/api")


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=PORT, reload=True)
