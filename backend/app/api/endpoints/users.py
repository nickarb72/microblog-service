import fastapi
from fastapi import APIRouter, Depends, HTTPException, status, Header, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update
from typing import List

from sqlalchemy.orm import selectinload

from backend.app.db.session import get_db
from backend.app.db.models import Tweet, TweetMedia, Like, Follow, User
from backend.app.config import UPLOADS_DIR, ALLOWED_TYPES, MAX_FILE_SIZE
from backend.app.schemas import (
    TweetCreateRequest,
    TweetCreateResponse,
    ErrorResponse,
    MediaUploadResponse,
    MediaFileForm, TweetDeleteLikeFollowResponse, UserResponse
)
from backend.app.db.utils import get_user_by_api_key, get_tweet_by_id, get_like_by_tweet_and_user_id, get_user_by_id, \
    get_follow_by_users_id
from backend.app.api.utils import api_error, format_user

router = APIRouter()


@router.post(
    "/users/{user_id}/follow",
    response_model=TweetDeleteLikeFollowResponse,
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        413: {"model": ErrorResponse}
    },
    summary="Follow a user",
    description="Follow a user by user ID",
    tags=["users"]
)
async def create_follow(
    api_key: str = Header(..., alias="api-key"),
    user_id: int = fastapi.Path(..., ge=1),
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

        following = await get_user_by_id(db, user_id)
        if not following or following.id == user.id:
            return api_error(
                error_type="not_found",
                error_message="User not found or you try to follow yourself",
                status_code=status.HTTP_404_NOT_FOUND
            )

        follow = Follow(
            follower_id=user.id,
            following_id=following.id
        )

        db.add(follow)

        return TweetDeleteLikeFollowResponse(result=True)

    except Exception as e:
        return api_error(
            error_type="server_error",
            error_message=str(e),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.delete(
    "/users/{user_id}/follow",
    response_model=TweetDeleteLikeFollowResponse,
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        413: {"model": ErrorResponse}
    },
    summary="Remove follow a user",
    description="Remove follow a user by user ID",
    tags=["users"]
)
async def delete_follow(
    api_key: str = Header(..., alias="api-key"),
    user_id: int = fastapi.Path(..., ge=1),
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

        follow = await get_follow_by_users_id(db, user.id, user_id)
        if not follow:
            return api_error(
                error_type="not_found",
                error_message="Follow not found",
                status_code=status.HTTP_404_NOT_FOUND
            )

        await db.delete(follow)

        return TweetDeleteLikeFollowResponse(result=True)

    except Exception as e:
        return api_error(
            error_type="server_error",
            error_message=str(e),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.get(
    "/users/me",
    response_model=UserResponse,
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    },
    summary="Get current user profile",
    description="Returns detailed profile information including followers and following",
    tags=["users"]
)
async def get_current_user_profile(
        api_key: str = Header(..., alias="api-key"),
        db: AsyncSession = Depends(get_db)
):
    try:
        user = await db.execute(
            select(User)
            .options(
                selectinload(User.followers).joinedload(Follow.follower),
                selectinload(User.following).joinedload(Follow.following)
            )
            .where(User.api_key == api_key)
        )
        user = user.scalar_one_or_none()
        if not user:
            return api_error(
                error_type="authentication_error",
                error_message="Invalid API key",
                status_code=status.HTTP_401_UNAUTHORIZED
            )

        formatted_user = format_user(user)

        return {
            "result": True,
            "user": formatted_user
        }

    except Exception as e:
        return api_error(
            error_type="server_error",
            error_message=str(e),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.get(
    "/users/{user_id}",
    response_model=UserResponse,
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    },
    summary="Get any user profile",
    description="Returns detailed profile information including followers and following by user ID",
    tags=["users"]
)
async def get_any_user_profile(
        user_id: int = fastapi.Path(..., ge=1),
        db: AsyncSession = Depends(get_db)
):
    try:
        user = await db.execute(
            select(User)
            .options(
                selectinload(User.followers).joinedload(Follow.follower),
                selectinload(User.following).joinedload(Follow.following)
            )
            .where(User.id == user_id)
        )
        user = user.scalar_one_or_none()
        if not user:
            return api_error(
                error_type="not_found",
                error_message="User not found",
                status_code=status.HTTP_404_NOT_FOUND
            )

        formatted_user = format_user(user)

        return {
            "result": True,
            "user": formatted_user
        }

    except Exception as e:
        return api_error(
            error_type="server_error",
            error_message=str(e),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )