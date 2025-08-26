# DROP DATABASE microblog_db;
# CREATE DATABASE microblog_db;
# GRANT ALL PRIVILEGES ON SCHEMA public TO admin;
# GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO admin;
# ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO admin;

import asyncio
import random
import shutil
import uuid
from pathlib import Path

from faker import Faker
from PIL import Image
from sqlalchemy import insert, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import UPLOADS_DIR, MAX_TEXT_SIZE
from backend.app.db.models import Follow, Like, Tweet, TweetMedia, User
from backend.app.db.session import AsyncSessionLocal, Base, engine

MAX_NUMBER_OF_COLOR = 255
NUMBER_OF_LIKES = 30
PERCENTAGE = 0.7

fake = Faker()


async def fill_test_db(session: AsyncSession):
    if UPLOADS_DIR.exists():
        shutil.rmtree(UPLOADS_DIR)
    UPLOADS_DIR.mkdir()

    users_data = [
        {"name": "Test User", "api_key": "test"},
        *[{"name": fake.name(), "api_key": fake.uuid4()} for _ in range(4)],
    ]

    cor_users = await session.execute(insert(User).returning(User.id), users_data)
    user_ids = cor_users.scalars().all()
    main_user_id = user_ids[0]

    tweets_data = [
        {
            "content": fake.text(max_nb_chars=MAX_TEXT_SIZE),
            "user_id": random.choice(user_ids),
        }
        for _ in range(10)
    ]
    cor_tweets = await session.execute(insert(Tweet).returning(Tweet.id), tweets_data)
    tweet_ids = cor_tweets.scalars().all()
    for tweet, tweet_id in zip(tweets_data, tweet_ids):
        tweet["id"] = tweet_id

    all_media = []
    for tweet in tweets_data:
        num_media = random.choice([0, 1, 1, 2, 2, 3])
        for _ in range(num_media):
            file_ext = random.choice(["jpg", "png"])
            filename = f"{uuid.uuid4()}.{file_ext}"
            file_path = UPLOADS_DIR / filename

            img = Image.new(
                "RGB",
                (100, 100),
                color=(
                    random.randint(0, MAX_NUMBER_OF_COLOR),
                    random.randint(0, MAX_NUMBER_OF_COLOR),
                    random.randint(0, MAX_NUMBER_OF_COLOR),
                ),
            )
            img.save(file_path)

            all_media.append(
                {
                    "url": str(Path("uploads") / filename),
                    "tweet_id": tweet["id"],
                    "user_id": tweet["user_id"],
                }
            )
    if all_media:
        await session.execute(insert(TweetMedia), all_media)

    follows_data = []
    unique_pairs = set()
    following_ids = []

    while len(unique_pairs) < 3:
        following_id = random.choice(user_ids[1:])
        pair = (main_user_id, following_id)

        if pair not in unique_pairs:
            unique_pairs.add(pair)
            following_ids.append(following_id)
            follows_data.append(
                {"follower_id": main_user_id, "following_id": following_id}
            )

    while len(unique_pairs) < 10:
        follower, following = random.sample(user_ids[1:], 2)
        pair = (follower, following)

        if follower != following and pair not in unique_pairs:
            unique_pairs.add(pair)
            follows_data.append({"follower_id": follower, "following_id": following})
    await session.execute(insert(Follow), follows_data)

    likes_data = []
    unique_pairs.clear()

    while len(unique_pairs) < NUMBER_OF_LIKES:
        if random.random() < PERCENTAGE:
            pair = (random.choice(following_ids), random.choice(tweet_ids))
        else:
            pair = (random.choice(user_ids), random.choice(tweet_ids))

        if pair not in unique_pairs:
            unique_pairs.add(pair)
            likes_data.append({"user_id": pair[0], "tweet_id": pair[1]})
    await session.execute(insert(Like), likes_data)


async def create_test_data(session: AsyncSession):
    try:
        await fill_test_db(session)
        await session.commit()
    except Exception as exc:
        await session.rollback()
        print(f"\n❌ Exception has occurred while test data was creating: {exc}")
        raise

    print("\n✅ Test data created")
    print("🔑 API key of Test User: test")
    print("🆔 ID of Test User: 1")
    print("📁 Test media files created in the folder 'uploads'")


async def init_db_with_test_data():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        async with session.begin():
            await create_test_data(session)


if __name__ == "__main__":
    asyncio.run(init_db_with_test_data())
