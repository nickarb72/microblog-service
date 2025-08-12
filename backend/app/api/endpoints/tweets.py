import os
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status, Header, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update
from typing import List

from backend.app.db.session import get_db
from backend.app.db.models import Tweet, TweetMedia
from backend.app.config import UPLOADS_DIR, ALLOWED_TYPES, MAX_FILE_SIZE
from backend.app.schemas import (
    TweetCreateRequest,
    TweetCreateResponse,
    ErrorResponse,
    MediaUploadResponse,
    MediaFileForm
)
from backend.app.db.utils import get_user_by_api_key
from backend.app.api.utils import api_error

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