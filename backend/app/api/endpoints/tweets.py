import asyncio
import os
import uuid
from pathlib import Path

import fastapi
from fastapi import APIRouter, Depends, HTTPException, status, Header, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update
from typing import List

from sqlalchemy.orm import selectinload

from backend.app.db.session import get_db
from backend.app.db.models import Tweet, TweetMedia, Like, User, Follow
from backend.app.config import UPLOADS_DIR, ALLOWED_TYPES, MAX_FILE_SIZE
from backend.app.schemas import (
    TweetCreateRequest,
    TweetCreateResponse,
    ErrorResponse,
    MediaUploadResponse,
    MediaFileForm, TweetDeleteLikeFollowResponse, TweetsFeedResponse
)
from backend.app.db.utils import get_user_by_api_key, get_tweet_by_id, get_like_by_tweet_and_user_id
from backend.app.api.utils import api_error, format_tweets

router = APIRouter()


@router.post(
    "/tweets",
    response_model=TweetCreateResponse,
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse}
    },
    summary="Create a new tweet",
    description="Creates a tweet with optional media attachments",
    tags=["tweets"]
)
async def create_tweet(
        tweet_data: TweetCreateRequest,
        api_key: str = Header(..., alias="api-key"),
        db: AsyncSession = Depends(get_db)
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
                    status_code=status.HTTP_401_UNAUTHORIZED
                )

        if tweet_data.tweet_media_ids:
            media_count = await db.execute(
                select(func.count(TweetMedia.id)).where(
                    TweetMedia.id.in_(tweet_data.tweet_media_ids),
                    TweetMedia.user_id == user.id
                )
            )
            if media_count.scalar() != len(tweet_data.tweet_media_ids):
                return api_error(
                    error_type="not_found",
                    error_message="Some media files not found",
                    status_code=status.HTTP_404_NOT_FOUND
                )

        tweet = Tweet(
            content=tweet_data.tweet_data,
            user_id=user.id
        )

        db.add(tweet)
        await db.flush()

        if tweet_data.tweet_media_ids:
            await db.execute(
                update(TweetMedia)
                .where(TweetMedia.id.in_(tweet_data.tweet_media_ids))
                .values(tweet_id=tweet.id)
            )

        return TweetCreateResponse(
            result=True,
            tweet_id=tweet.id
        )

    except HTTPException as he:
        return api_error(
            error_type="http_error",
            error_message=str(he.detail),
            status_code=he.status_code
        )

    except ValueError as e:
        return api_error(
            error_type="validation_error",
            error_message=str(e)
        )

    except Exception as e:
        return api_error(
            error_type="server_error",
            error_message=str(e),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.post(
    "/medias",
    response_model=MediaUploadResponse,
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        413: {"model": ErrorResponse}
    },
    summary="Upload media file",
    description="Upload image file (JPEG/PNG, max 5MB)",
    tags=["tweets"]
)
async def upload_media(
    api_key: str = Header(..., alias="api-key"),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    try:
        user = await get_user_by_api_key(db, api_key)
        if not user:
            return api_error(
                error_type="authentication_error",
                error_message="Invalid API key",
                status_code=status.HTTP_401_UNAUTHORIZED
            )

        if file.content_type not in ALLOWED_TYPES:
            return api_error(
                error_type="validation_error",
                error_message="Only JPEG/PNG images allowed",
            )

        file.file.seek(0, os.SEEK_END)
        file_size = file.file.tell()
        file.file.seek(0)
        if file_size > MAX_FILE_SIZE:
            return api_error(
                error_type="validation_error",
                error_message=f"File too large. Max size: {MAX_FILE_SIZE//1024//1024}MB",
                status_code=413
            )

        file_ext = file.filename.split(".")[-1]
        filename = f"{uuid.uuid4()}.{file_ext}"
        file_path = UPLOADS_DIR / filename

        with open(file_path, "wb") as buffer:
            buffer.write(await file.read())

        relative_path = str(Path("uploads") / filename)

        media = TweetMedia(
            user_id=user.id,
            url=relative_path,
        )

        db.add(media)
        await db.flush()

        return MediaUploadResponse(
            result=True,
            media_id=media.id
        )

    except Exception as e:
        return api_error(
            error_type="server_error",
            error_message=str(e),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.delete(
    "/tweets/{tweet_id}",
    response_model=TweetDeleteLikeFollowResponse,
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        413: {"model": ErrorResponse}
    },
    summary="Delete the tweet",
    description="Delete the tweet by tweet ID",
    tags=["tweets"]
)
async def delete_tweet(
    api_key: str = Header(..., alias="api-key"),
    tweet_id: int = fastapi.Path(..., ge=1),
    db: AsyncSession = Depends(get_db)
):
    try:
        user = await get_user_by_api_key(db, api_key)
        if not user:
            return api_error(
                error_type="authentication_error",
                error_message="Invalid API key",
                status_code=status.HTTP_401_UNAUTHORIZED
            )

        tweet = await get_tweet_by_id(db, tweet_id)
        if not tweet or tweet.user_id != user.id:
            return api_error(
                error_type="not_found",
                error_message="Tweet not found or belongs to another user",
                status_code=status.HTTP_404_NOT_FOUND
            )

        result = await db.execute(
            select(TweetMedia.url).where(TweetMedia.tweet_id == tweet_id)
        )
        relative_file_paths = result.scalars().all()

        for relative_file_path in relative_file_paths:
            file_path = str(UPLOADS_DIR / Path(relative_file_path).name)
            if os.path.exists(file_path):
                await asyncio.to_thread(os.remove, file_path)

        await db.delete(tweet)

        return TweetDeleteLikeFollowResponse(result=True)

    except Exception as e:
        return api_error(
            error_type="server_error",
            error_message=str(e),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.post(
    "/tweets/{tweet_id}/likes",
    response_model=TweetDeleteLikeFollowResponse,
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        413: {"model": ErrorResponse}
    },
    summary="Like a tweet",
    description="Like a tweet by tweet ID",
    tags=["tweets"]
)
async def create_like(
    api_key: str = Header(..., alias="api-key"),
    tweet_id: int = fastapi.Path(..., ge=1),
    db: AsyncSession = Depends(get_db)
):
    try:
        user = await get_user_by_api_key(db, api_key)
        if not user:
            return api_error(
                error_type="authentication_error",
                error_message="Invalid API key",
                status_code=status.HTTP_401_UNAUTHORIZED
            )

        tweet = await get_tweet_by_id(db, tweet_id)
        like = await get_like_by_tweet_and_user_id(db, tweet_id, user.id)
        if not tweet or like:
            return api_error(
                error_type="not_found",
                error_message="Tweet not found or like already exists",
                status_code=status.HTTP_404_NOT_FOUND
            )

        like = Like(
            tweet_id=tweet_id,
            user_id=user.id
        )

        db.add(like)

        return TweetDeleteLikeFollowResponse(result=True)

    except Exception as e:
        return api_error(
            error_type="server_error",
            error_message=str(e),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.delete(
    "/tweets/{tweet_id}/likes",
    response_model=TweetDeleteLikeFollowResponse,
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        413: {"model": ErrorResponse}
    },
    summary="Remove like from the tweet",
    description="Remove like from the tweet by tweet ID",
    tags=["tweets"]
)
async def delete_like(
    api_key: str = Header(..., alias="api-key"),
    tweet_id: int = fastapi.Path(..., ge=1),
    db: AsyncSession = Depends(get_db)
):
    try:
        user = await get_user_by_api_key(db, api_key)
        if not user:
            return api_error(
                error_type="authentication_error",
                error_message="Invalid API key",
                status_code=status.HTTP_401_UNAUTHORIZED
            )

        like = await get_like_by_tweet_and_user_id(db, tweet_id, user.id)
        if not like:
            return api_error(
                error_type="not_found",
                error_message="Like not found",
                status_code=status.HTTP_404_NOT_FOUND
            )

        await db.delete(like)

        return TweetDeleteLikeFollowResponse(result=True)

    except Exception as e:
        return api_error(
            error_type="server_error",
            error_message=str(e),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.get(
    "/tweets",
    response_model=TweetsFeedResponse,
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    },
    summary="Get user's tweet feed",
    description="Returns a list of tweets from users the current user follows",
    tags=["tweets"]
)
async def get_tweets_feed(
        api_key: str = Header(..., alias="api-key"),
        db: AsyncSession = Depends(get_db)
):
    try:
        user = await get_user_by_api_key(db, api_key)
        if not user:
            return api_error(
                error_type="authentication_error",
                error_message="Invalid API key",
                status_code=status.HTTP_401_UNAUTHORIZED
            )

        query = (
            select(Tweet)
            .join(User, Tweet.user_id == User.id)
            .join(
                Follow,
                Follow.following_id == Tweet.user_id,
                isouter=True
            )
            .where(
                (Follow.follower_id == user.id) |
                (Tweet.user_id == user.id)
            )
            .options(
                selectinload(Tweet.author),
                selectinload(Tweet.likes).joinedload(Like.user),
                selectinload(Tweet.media)
            )
        )

        result = await db.execute(query)
        tweets = result.scalars().all()

        formatted_tweets = format_tweets(tweets)

        return {
            "result": True,
            "tweets": formatted_tweets
        }

    except Exception as e:
        return api_error(
            error_type="server_error",
            error_message=str(e),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )