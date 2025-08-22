import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from backend.app.api.endpoints import tweets, users
from backend.app.db.models import Follow, Like, Tweet, TweetMedia, User
from backend.app.db.session import AsyncSessionLocal, Base, engine
from backend.scripts.fill_db import fill_test_db


@pytest_asyncio.fixture()
async def test_data(db_session):
    await fill_test_db(db_session)
    await db_session.commit()

    result = await db_session.execute(select(User))
    users = result.scalars().all()
    main_user = users[0]

    result = await db_session.execute(select(Tweet))
    tweets = result.scalars().all()

    result = await db_session.execute(select(TweetMedia))
    media = result.scalars().all()

    result = await db_session.execute(select(Like))
    likes = result.scalars().all()

    result = await db_session.execute(select(Follow))
    follows = result.scalars().all()

    yield {
        "main_user": main_user,
        "users": users,
        "tweets": tweets,
        "media": media,
        "likes": likes,
        "follows": follows,
    }


@pytest_asyncio.fixture()
async def db_session(db_session_factory):
    async with db_session_factory() as session:
        yield session
        await session.rollback()
        await session.close()


@pytest_asyncio.fixture()
async def client():
    from backend.app.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client


# @pytest.fixture()
# def client():
#     from backend.app.main import app
#
#     with TestClient(app) as test_client:
#         yield test_client


@pytest_asyncio.fixture()
async def db_session_factory():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    yield AsyncSessionLocal

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()
