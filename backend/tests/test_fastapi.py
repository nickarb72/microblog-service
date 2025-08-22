# python -m pytest --cov=app tests/
# python -m pytest --cov=app --cov-report=term-missing tests/

import os
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy import insert, select

from backend.app.api.endpoints import tweets, users
from backend.app.config import UPLOADS_DIR
from backend.app.db.models import Follow, Like, Tweet, TweetMedia, User


@pytest.mark.asyncio
async def test_create_tweet_success(test_data, client):
    api_key = test_data["main_user"].api_key
    headers = {"api-key": api_key}

    payload = {"tweet_data": "This is a test tweet", "tweet_media_ids": []}

    response = await client.post("/api/tweets", json=payload, headers=headers)

    assert response.status_code == 200
    assert response.json()["result"] is True
    assert "tweet_id" in response.json()


@pytest.mark.asyncio
async def test_create_tweet_authentication_error(client, test_data):
    headers = {"api-key": "invalid_key"}

    payload = {"tweet_data": "This is a test tweet", "tweet_media_ids": []}

    response = await client.post("/api/tweets", json=payload, headers=headers)

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_tweet_not_found_error(test_data, client):
    api_key = test_data["main_user"].api_key
    headers = {"api-key": api_key}

    payload = {"tweet_data": "This is a test tweet", "tweet_media_ids": [999999]}

    response = await client.post("/api/tweets", json=payload, headers=headers)

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_upload_media_success(client, test_data):
    api_key = test_data["main_user"].api_key
    headers = {"api-key": api_key}

    test_image_path = str(UPLOADS_DIR / Path("test_image.png"))
    png_header = bytes.fromhex("89504E470D0A1A0A")
    fake_data = bytes([0] * 100)
    fake_png_data = png_header + fake_data
    with open(test_image_path, "wb") as test_image:
        test_image.write(fake_png_data)

    with open(test_image_path, "rb") as file:
        response = await client.post(
            "/api/medias",
            files={"upload_file": ("test_image.png", file, "image/png")},
            headers=headers,
        )

    assert response.status_code == 200
    assert response.json()["result"] is True
    assert "media_id" in response.json()
    assert os.path.exists(test_image_path)


@pytest.mark.asyncio
async def test_upload_media_authentication_error(client, test_data):
    headers = {"api-key": "invalid_key"}

    test_image_path = str(UPLOADS_DIR / Path("test_image.png"))
    png_header = bytes.fromhex("89504E470D0A1A0A")
    fake_data = bytes([0] * 100)
    fake_png_data = png_header + fake_data
    with open(test_image_path, "wb") as test_image:
        test_image.write(fake_png_data)

    with open(test_image_path, "rb") as file:
        response = await client.post(
            "/api/medias",
            files={"upload_file": ("test_image.png", file, "image/png")},
            headers=headers,
        )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_upload_media_invalid_filetype(client, test_data):
    api_key = test_data["main_user"].api_key
    headers = {"api-key": api_key}

    test_file_path = str(UPLOADS_DIR / Path("test_file.txt"))
    with open(test_file_path, "wb") as test_file:
        test_file.write(b"fake text data")

    with open(test_file_path, "rb") as file:
        response = await client.post(
            "/api/medias",
            files={"upload_file": ("test_file.txt", file, "text/plain")},
            headers=headers,
        )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_upload_media_file_too_large(client, test_data):
    api_key = test_data["main_user"].api_key
    headers = {"api-key": api_key}

    test_image_path = str(UPLOADS_DIR / Path("large_image.png"))
    with open(test_image_path, "wb") as test_image:
        test_image.write(b"a" * (5 * 1024 * 1024 + 1))

    with open(test_image_path, "rb") as file:
        response = await client.post(
            "/api/medias",
            files={"upload_file": ("large_image.png", file, "image/png")},
            headers=headers,
        )

    assert response.status_code == 413


@pytest.mark.asyncio
async def test_delete_tweet_cascades_media(db_session, test_data, client):
    users = test_data["users"]
    media = test_data["media"]

    file_path = str(UPLOADS_DIR / Path(media[0].url).name)
    assert os.path.exists(file_path)

    tweet_exists = await db_session.execute(
        select(Tweet).where(Tweet.id == media[0].tweet_id)
    )
    assert tweet_exists.scalar_one_or_none()

    response = await client.delete(
        f"/api/tweets/{media[0].tweet_id}",
        headers={"api-key": users[media[0].user_id - 1].api_key},
    )

    assert response.status_code == 200
    assert response.json()["result"] is True

    media_exists = await db_session.execute(
        select(TweetMedia).where(TweetMedia.id == media[0].id)
    )
    assert media_exists.scalar_one_or_none() is None
    assert not os.path.exists(file_path)


@pytest.mark.asyncio
async def test_create_like_success(client, test_data, db_session):
    api_key = test_data["main_user"].api_key
    headers = {"api-key": api_key}

    tweets_data = [
        {
            "content": "Test content",
            "user_id": test_data["main_user"].id,
        }
    ]
    result = await db_session.execute(insert(Tweet).returning(Tweet.id), tweets_data)
    tweet_ids = result.scalars().all()
    await db_session.commit()
    tweet_id = tweet_ids[0]

    result = await db_session.execute(select(Like))
    number_of_likes = len(result.scalars().all())

    response = await client.post(f"/api/tweets/{tweet_id}/likes", headers=headers)

    assert response.status_code == 200
    assert response.json()["result"] is True

    result = await db_session.execute(select(Like))
    assert len(result.scalars().all()) == number_of_likes + 1


@pytest.mark.asyncio
async def test_create_like_authentication_error(client, test_data):
    headers = {"api-key": "invalid_key"}

    tweet_id = test_data["tweets"][0].id

    response = await client.post(f"/api/tweets/{tweet_id}/likes", headers=headers)

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_like_tweet_not_found(client, test_data):
    api_key = test_data["main_user"].api_key
    headers = {"api-key": api_key}

    tweet_id = 999999

    response = await client.post(f"/tweets/{tweet_id}/likes", headers=headers)

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_like_already_exists(client, test_data, db_session):
    tweet_id = test_data["likes"][0].tweet_id
    user_id = test_data["likes"][0].user_id
    api_key = test_data["users"][user_id - 1].api_key

    headers = {"api-key": api_key}

    like = await db_session.execute(
        select(Like).where(Like.user_id == user_id, Like.tweet_id == tweet_id)
    )
    assert like.scalar_one_or_none()

    response = await client.post(f"/api/tweets/{tweet_id}/likes", headers=headers)

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_create_like_server_error(client, test_data, mocker):
    api_key = test_data["main_user"].api_key
    tweet_id = test_data["tweets"][0].id

    headers = {"api-key": api_key}

    with mocker.patch(
        "backend.app.api.endpoints.tweets.get_tweet_by_id",
        side_effect=Exception("Unexpected error"),
    ):
        response = await client.post(f"/api/tweets/{tweet_id}/likes", headers=headers)

        assert response.status_code == 500


@pytest.mark.asyncio
async def test_delete_like_success(client, test_data, db_session):
    tweet_id = test_data["likes"][0].tweet_id
    user_id = test_data["likes"][0].user_id
    api_key = test_data["users"][user_id - 1].api_key

    headers = {"api-key": api_key}

    result = await db_session.execute(select(Like))
    number_of_likes = len(result.scalars().all())

    response = await client.delete(f"/api/tweets/{tweet_id}/likes", headers=headers)

    assert response.status_code == 200
    assert response.json()["result"] is True

    result = await db_session.execute(select(Like))
    assert len(result.scalars().all()) == number_of_likes - 1


@pytest.mark.asyncio
async def test_delete_like_authentication_error(client, test_data):
    headers = {"api-key": "invalid_key"}

    tweet_id = test_data["tweets"][0].id

    response = await client.delete(f"/api/tweets/{tweet_id}/likes", headers=headers)

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_delete_like_not_found(client, test_data):
    api_key = test_data["main_user"].api_key
    headers = {"api-key": api_key}

    tweet_id = 999999

    response = await client.delete(f"/api/tweets/{tweet_id}/likes", headers=headers)

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_like_server_error(client, test_data, mocker):
    api_key = test_data["main_user"].api_key
    tweet_id = test_data["tweets"][0].id

    headers = {"api-key": api_key}

    mocker.patch(
        "backend.app.api.endpoints.tweets.get_like_by_tweet_and_user_id",
        side_effect=Exception("Unexpected error"),
    )

    response = await client.delete(f"/api/tweets/{tweet_id}/likes", headers=headers)

    assert response.status_code == 500


@pytest.mark.asyncio
async def test_create_follow_success(client, test_data, db_session):
    api_key = test_data["main_user"].api_key
    headers = {"api-key": api_key}

    users_data = [
        {
            "name": "follow name",
            "api_key": "follow api key",
        }
    ]
    result = await db_session.execute(insert(User).returning(User.id), users_data)
    user_ids = result.scalars().all()
    await db_session.commit()
    user_id = user_ids[0]

    result = await db_session.execute(select(Follow))
    number_of_follows = len(result.scalars().all())

    response = await client.post(f"/api/users/{user_id}/follow", headers=headers)

    assert response.status_code == 200
    assert response.json()["result"] is True

    result = await db_session.execute(select(Follow))
    assert len(result.scalars().all()) == number_of_follows + 1


@pytest.mark.asyncio
async def test_create_follow_authentication_error(client, test_data):
    headers = {"api-key": "invalid_key"}

    user_id = test_data["users"][0].id

    response = await client.post(f"/api/users/{user_id}/follow", headers=headers)

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_follow_user_not_found(client, test_data):
    api_key = test_data["main_user"].api_key
    headers = {"api-key": api_key}

    user_id = test_data["main_user"].id

    response = await client.post(f"/users/{user_id}/follow", headers=headers)

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_follow_already_exists(client, test_data, db_session):
    follower_id = test_data["follows"][0].follower_id
    following_id = test_data["follows"][0].following_id
    api_key = test_data["users"][follower_id - 1].api_key

    headers = {"api-key": api_key}

    follow = await db_session.execute(
        select(Follow).where(
            Follow.follower_id == follower_id, Follow.following_id == following_id
        )
    )
    assert follow.scalar_one_or_none()

    response = await client.post(f"/api/users/{following_id}/follow", headers=headers)

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_create_follow_server_error(client, test_data, mocker):
    api_key = test_data["main_user"].api_key
    user_id = test_data["users"][0].id

    headers = {"api-key": api_key}

    with mocker.patch(
        "backend.app.api.endpoints.users.get_user_by_id",
        side_effect=Exception("Unexpected error"),
    ):
        response = await client.post(f"/api/users/{user_id}/follow", headers=headers)

        assert response.status_code == 500


@pytest.mark.asyncio
async def test_delete_follow_success(client, test_data, db_session):
    follower_id = test_data["follows"][0].follower_id
    following_id = test_data["follows"][0].following_id
    api_key = test_data["users"][follower_id - 1].api_key

    headers = {"api-key": api_key}

    result = await db_session.execute(select(Follow))
    number_of_follows = len(result.scalars().all())

    response = await client.delete(f"/api/users/{following_id}/follow", headers=headers)

    assert response.status_code == 200
    assert response.json()["result"] is True

    result = await db_session.execute(select(Follow))
    assert len(result.scalars().all()) == number_of_follows - 1


@pytest.mark.asyncio
async def test_delete_follow_authentication_error(client, test_data):
    headers = {"api-key": "invalid_key"}

    user_id = test_data["users"][0].id

    response = await client.delete(f"/api/users/{user_id}/follow", headers=headers)

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_delete_follow_not_found(client, test_data):
    api_key = test_data["main_user"].api_key
    headers = {"api-key": api_key}

    user_id = 999999

    response = await client.delete(f"/api/users/{user_id}/follow", headers=headers)

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_follow_server_error(client, test_data, mocker):
    api_key = test_data["main_user"].api_key
    user_id = test_data["users"][0].id

    headers = {"api-key": api_key}

    mocker.patch(
        "backend.app.api.endpoints.users.get_follow_by_users_id",
        side_effect=Exception("Unexpected error"),
    )

    response = await client.delete(f"/api/users/{user_id}/follow", headers=headers)

    assert response.status_code == 500


@pytest.mark.asyncio
async def test_get_tweets_feed_success(client, test_data):
    api_key = test_data["main_user"].api_key
    headers = {"api-key": api_key}

    response = await client.get("/api/tweets", headers=headers)

    assert response.status_code == 200
    assert response.json()["result"] is True
    assert isinstance(response.json()["tweets"], list)


@pytest.mark.asyncio
async def test_get_tweets_feed_authentication_error(client, test_data):
    headers = {"api-key": "invalid_key"}

    response = await client.get("/api/tweets", headers=headers)

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_tweets_feed_server_error(client, test_data, mocker):
    api_key = test_data["main_user"].api_key
    headers = {"api-key": api_key}

    mocker.patch(
        "backend.app.api.endpoints.tweets.get_user_by_api_key",
        side_effect=Exception("Unexpected error"),
    )

    response = await client.get("/api/tweets", headers=headers)

    assert response.status_code == 500


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "endpoint, headers, user_id, expected_status",
    [
        ("/api/users/me", {"api-key": "test"}, None, 200),
        ("/api/users/me", {"api-key": "invalid_key"}, None, 401),
        ("/api/users/{user_id}", {}, 1, 200),
        ("/api/users/{user_id}", {}, 999999, 404),
    ],
)
async def test_get_user_profile(
    endpoint, headers, user_id, expected_status, client, test_data
):
    if user_id is not None:
        endpoint = endpoint.format(user_id=user_id)

    response = await client.get(endpoint, headers=headers)

    assert response.status_code == expected_status

    if expected_status == 200:
        assert response.json()["result"] is True
        assert "user" in response.json()


@pytest.mark.asyncio
async def test_get_user_profile_server_error(client, test_data, mocker):
    headers = {"api-key": test_data["main_user"].api_key}

    mocker.patch(
        "backend.app.api.endpoints.users.format_user",
        side_effect=Exception("Unexpected error"),
    )

    response = await client.get("/api/users/me", headers=headers)

    assert response.status_code == 500
