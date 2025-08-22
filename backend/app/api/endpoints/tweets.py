import asyncio
import os
import uuid
import pathlib
from typing import List

from fastapi import (
    APIRouter,
    Depends,
    File,
    Header,
    HTTPException,
    Path,
    UploadFile,
    status,
)
from sqlalchemy import and_, desc, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.api.api_utils import api_error, format_tweets
from backend.app.config import (
    ALLOWED_TYPES,
    MAX_FILE_SIZE,
    MAX_FILE_SIZE_MB,
    UPLOADS_DIR,
)
from backend.app.db.models import Follow, Like, Tweet, TweetMedia, User
from backend.app.db.session import get_db
from backend.app.db.db_utils import (
    get_like_by_tweet_and_user_id,
    get_tweet_by_id,
    get_user_by_api_key,
)
from backend.app.schemas import (
    ErrorResponse,
    MediaUploadResponse,
    TweetCreateRequest,
    TweetCreateResponse,
    TweetDeleteLikeFollowResponse,
    TweetsFeedResponse,
)

HTTP_PAYLOAD_TOO_LARGE = 413
RESPONSE_MODEL = "model"
TAG = "tweets"

router = APIRouter()


@router.post(
    "/tweets",
    response_model=TweetCreateResponse,
    responses={
        400: {RESPONSE_MODEL: ErrorResponse},
        401: {RESPONSE_MODEL: ErrorResponse},
        404: {RESPONSE_MODEL: ErrorResponse},
    },
    summary="Create a new tweet",
    description="Creates a tweet with optional media attachments",
    tags=[TAG],
)
async def create_tweet(
    tweet_data: TweetCreateRequest,
    api_key: str = Header(..., alias="api-key"),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new tweet for authenticated user

    Args:
        tweet_data: Tweet content and optional media IDs
        api_key: User authentication key (in headers)
        db: Async database session

    Returns:
        TweetCreateResponse with new tweet ID if successful

    Raises:
        HTTPException: With appropriate status code for errors
    """
    try:
        user = await get_user_by_api_key(db, api_key)
        if not user:
            return api_error(
                error_type="authentication_error",
                error_message="Invalid API key",
                status_code=status.HTTP_401_UNAUTHORIZED,
            )

        if tweet_data.tweet_media_ids:
            media_count = await db.execute(
                select(func.count(TweetMedia.id)).where(
                    TweetMedia.id.in_(tweet_data.tweet_media_ids),
                    TweetMedia.user_id == user.id,
                )
            )
            if media_count.scalar() != len(tweet_data.tweet_media_ids):
                return api_error(
                    error_type="not_found",
                    error_message="Some media files not found",
                    status_code=status.HTTP_404_NOT_FOUND,
                )

        tweet = Tweet(content=tweet_data.tweet_data, user_id=user.id)

        db.add(tweet)
        await db.flush()

        if tweet_data.tweet_media_ids:
            await db.execute(
                update(TweetMedia)
                .where(TweetMedia.id.in_(tweet_data.tweet_media_ids))
                .values(tweet_id=tweet.id)
            )

        return TweetCreateResponse(result=True, tweet_id=tweet.id)

    except HTTPException as he:
        return api_error(
            error_type="http_error",
            error_message=str(he.detail),
            status_code=he.status_code,
        )

    except ValueError as exc:
        return api_error(error_type="validation_error", error_message=str(exc))

    except Exception as exc:
        return api_error(
            error_type="server_error",
            error_message=str(exc),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.post(
    "/medias",
    response_model=MediaUploadResponse,
    responses={
        400: {RESPONSE_MODEL: ErrorResponse},
        401: {RESPONSE_MODEL: ErrorResponse},
        413: {RESPONSE_MODEL: ErrorResponse},
    },
    summary="Upload media file",
    description="Upload image file (JPEG/PNG, max 5MB)",
    tags=[TAG],
)
async def upload_media(
    api_key: str = Header(..., alias="api-key"),
    upload_file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    try:
        user = await get_user_by_api_key(db, api_key)
        if not user:
            return api_error(
                error_type="authentication_error",
                error_message="Invalid API key",
                status_code=status.HTTP_401_UNAUTHORIZED,
            )

        if upload_file.content_type not in ALLOWED_TYPES:
            return api_error(
                error_type="validation_error",
                error_message="Only JPEG/PNG images allowed",
            )

        upload_file.file.seek(0, os.SEEK_END)
        file_size = upload_file.file.tell()
        upload_file.file.seek(0)
        if file_size > MAX_FILE_SIZE:
            return api_error(
                error_type="validation_error",
                error_message=f"File too large. Max size: " f"{MAX_FILE_SIZE_MB}MB",
                status_code=HTTP_PAYLOAD_TOO_LARGE,
            )

        file_ext = upload_file.filename.split(".")[-1]
        filename = f"{uuid.uuid4()}.{file_ext}"

        with open(UPLOADS_DIR / filename, "wb") as buffer:
            buffer.write(await upload_file.read())

        media = TweetMedia(
            user_id=user.id,
            url=str(pathlib.Path("uploads") / filename),
        )

        db.add(media)
        await db.flush()

        return MediaUploadResponse(result=True, media_id=media.id)

    except Exception as exc:
        return api_error(
            error_type="server_error",
            error_message=str(exc),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


async def delete_files(relative_file_paths: List[str]) -> None:
    delete_tasks = []

    for relative_file_path in relative_file_paths:
        file_path = UPLOADS_DIR / pathlib.Path(relative_file_path).name

        if file_path.exists():
            delete_tasks.append(asyncio.to_thread(os.remove, str(file_path)))

    if delete_tasks:
        await asyncio.gather(*delete_tasks)


@router.delete(
    "/tweets/{tweet_id}",
    response_model=TweetDeleteLikeFollowResponse,
    responses={
        400: {RESPONSE_MODEL: ErrorResponse},
        401: {RESPONSE_MODEL: ErrorResponse},
        413: {RESPONSE_MODEL: ErrorResponse},
    },
    summary="Delete the tweet",
    description="Delete the tweet by tweet ID",
    tags=[TAG],
)
async def delete_tweet(
    api_key: str = Header(..., alias="api-key"),
    tweet_id: int = Path(..., ge=1),
    db: AsyncSession = Depends(get_db),
):
    try:
        user = await get_user_by_api_key(db, api_key)
        if not user:
            return api_error(
                error_type="authentication_error",
                error_message="Invalid API key",
                status_code=status.HTTP_401_UNAUTHORIZED,
            )

        tweet = await get_tweet_by_id(db, tweet_id)
        if not tweet or tweet.user_id != user.id:
            return api_error(
                error_type="not_found",
                error_message="Tweet not found or belongs to another user",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        medias = await db.execute(
            select(TweetMedia.url).where(TweetMedia.tweet_id == tweet_id)
        )
        relative_file_paths = medias.scalars().all()

        await delete_files(relative_file_paths)

        await db.delete(tweet)

        return TweetDeleteLikeFollowResponse(result=True)

    except Exception as exc:
        return api_error(
            error_type="server_error",
            error_message=str(exc),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.post(
    "/tweets/{tweet_id}/likes",
    response_model=TweetDeleteLikeFollowResponse,
    responses={
        400: {RESPONSE_MODEL: ErrorResponse},
        401: {RESPONSE_MODEL: ErrorResponse},
        413: {RESPONSE_MODEL: ErrorResponse},
    },
    summary="Like a tweet",
    description="Like a tweet by tweet ID",
    tags=[TAG],
)
async def create_like(
    api_key: str = Header(..., alias="api-key"),
    tweet_id: int = Path(..., ge=1),
    db: AsyncSession = Depends(get_db),
):
    try:
        user = await get_user_by_api_key(db, api_key)
        if not user:
            return api_error(
                error_type="authentication_error",
                error_message="Invalid API key",
                status_code=status.HTTP_401_UNAUTHORIZED,
            )

        tweet = await get_tweet_by_id(db, tweet_id)
        if not tweet:
            return api_error(
                error_type="not_found",
                error_message="Tweet not found",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        like = await get_like_by_tweet_and_user_id(db, tweet_id, user.id)
        if like:
            return api_error(
                error_type="like_already_exists",
                error_message="This like already exist",
                status_code=status.HTTP_409_CONFLICT,
            )

        like = Like(tweet_id=tweet_id, user_id=user.id)

        db.add(like)

        return TweetDeleteLikeFollowResponse(result=True)

    except Exception as exc:
        return api_error(
            error_type="server_error",
            error_message=str(exc),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.delete(
    "/tweets/{tweet_id}/likes",
    response_model=TweetDeleteLikeFollowResponse,
    responses={
        400: {RESPONSE_MODEL: ErrorResponse},
        401: {RESPONSE_MODEL: ErrorResponse},
        413: {RESPONSE_MODEL: ErrorResponse},
    },
    summary="Remove like from the tweet",
    description="Remove like from the tweet by tweet ID",
    tags=[TAG],
)
async def delete_like(
    api_key: str = Header(..., alias="api-key"),
    tweet_id: int = Path(..., ge=1),
    db: AsyncSession = Depends(get_db),
):
    try:
        user = await get_user_by_api_key(db, api_key)
        if not user:
            return api_error(
                error_type="authentication_error",
                error_message="Invalid API key",
                status_code=status.HTTP_401_UNAUTHORIZED,
            )

        like = await get_like_by_tweet_and_user_id(db, tweet_id, user.id)
        if not like:
            return api_error(
                error_type="not_found",
                error_message="Like not found",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        await db.delete(like)

        return TweetDeleteLikeFollowResponse(result=True)

    except Exception as exc:
        return api_error(
            error_type="server_error",
            error_message=str(exc),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.get(
    "/tweets",
    response_model=TweetsFeedResponse,
    responses={
        400: {RESPONSE_MODEL: ErrorResponse},
        401: {RESPONSE_MODEL: ErrorResponse},
        500: {RESPONSE_MODEL: ErrorResponse},
    },
    summary="Get user's tweet feed",
    description="Returns a list of tweets from users the current user follows",
    tags=[TAG],
)
async def get_tweets_feed(
    api_key: str = Header(..., alias="api-key"), db: AsyncSession = Depends(get_db)
):
    try:
        user = await get_user_by_api_key(db, api_key)
        if not user:
            return api_error(
                error_type="authentication_error",
                error_message="Invalid API key",
                status_code=status.HTTP_401_UNAUTHORIZED,
            )

        likes_subquery = (
            select(
                Like.tweet_id, func.count(Like.id).label("followed_user_likes_count")
            )
            .join(User, Like.user_id == User.id)
            .join(
                Follow,
                and_(Follow.following_id == User.id, Follow.follower_id == user.id),
            )
            .group_by(Like.tweet_id)
        ).cte("followed_user_likes")

        query = (
            select(Tweet)
            .join(User, Tweet.user_id == User.id)
            .outerjoin(
                Follow,
                and_(
                    Follow.following_id == Tweet.user_id, Follow.follower_id == user.id
                ),
            )
            .where((Follow.follower_id == user.id) | (Tweet.user_id == user.id))
            .outerjoin(likes_subquery, likes_subquery.c.tweet_id == Tweet.id)
            .order_by(desc(likes_subquery.c.followed_user_likes_count))
            .options(
                selectinload(Tweet.author),
                selectinload(Tweet.likes).joinedload(Like.user),
                selectinload(Tweet.media),
            )
        )

        cor_tweets = await db.execute(query)
        tweets = cor_tweets.scalars().all()

        return {"result": True, "tweets": format_tweets(tweets)}

    except Exception as exc:
        return api_error(
            error_type="server_error",
            error_message=str(exc),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
