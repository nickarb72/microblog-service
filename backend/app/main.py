from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from backend.app.config import UPLOADS_DIR
from backend.app.db.session import engine, Base
from backend.app.api.api import main_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        # await conn.run_sync(Base.metadata.create_all)
        pass

    UPLOADS_DIR.mkdir(exist_ok=True, parents=True)

    yield

    await engine.dispose()


app = FastAPI(
    title="Microblog API",
    description="API for microblogging service",
    version="1.0.0",
    lifespan=lifespan,
    openapi_tags=[
        {
            "name": "tweets",
            "description": "Operations with tweets"
        },
        {
            "name": "users",
            "description": "Operations with users",
        }
    ]
)

app.include_router(main_router, prefix="/api")


@app.get("/")
async def root():
    return {"message": "Microblog API is running"}


if __name__ == '__main__':
    uvicorn.run("main:app", host='127.0.0.1', port=8000, reload=True)
