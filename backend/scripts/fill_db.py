# DROP DATABASE microblog_db;
# CREATE DATABASE microblog_db;
# GRANT ALL PRIVILEGES ON SCHEMA public TO admin;
# GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO admin;
# ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO admin;

import asyncio
from faker import Faker
from sqlalchemy import text, insert
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import Base, engine, AsyncSessionLocal
from backend.app.db.models import User, Tweet, TweetMedia, Like, Follow

fake = Faker()


async def create_test_data(session: AsyncSession):
    users_data = [
        {"name": fake.name(), "api_key": "test"},
        *[{"name": fake.name(), "api_key": fake.uuid4()} for _ in range(4)]
    ]

    result = await session.execute(insert(User).returning(User.id), users_data)
    user_ids = result.scalars().all()

    # tweets_data = [
    #     {"content": fake.text(280), "user_id": user_ids[i % 5]} for i in range(20)
    # ]
    # await session.execute(insert(Tweet), tweets_data)
    #
    # follows_data = [
    #     {"follower_id": user_ids[i], "following_id": user_ids[(i + 1) % 5]}
    #     for i in range(5)
    # ]
    # await session.execute(insert(Follow), follows_data)

    print("✅ Тестовые данные созданы")


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        async with session.begin():
            await create_test_data(session)
            await session.commit()


if __name__ == "__main__":
    asyncio.run(init_db())