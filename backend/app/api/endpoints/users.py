from fastapi import APIRouter, Depends, Header, Path, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.api.api_utils import api_error, format_user
from backend.app.db.models import Follow, User
from backend.app.db.session import get_db
from backend.app.db.db_utils import (
    get_follow_by_users_id,
    get_user_by_api_key,
    get_user_by_id,
)
from backend.app.schemas import (
    ErrorResponse,
    TweetDeleteLikeFollowResponse,
    UserResponse,
)

RESPONSE_MODEL = "model"
TAG = "users"

router = APIRouter()


@router.post(
    "/users/{user_id}/follow",
    response_model=TweetDeleteLikeFollowResponse,
    responses={
        400: {RESPONSE_MODEL: ErrorResponse},
        401: {RESPONSE_MODEL: ErrorResponse},
        413: {RESPONSE_MODEL: ErrorResponse},
    },
    summary="Follow a user",
    description="Follow a user by user ID",
    tags=[TAG],
)
async def create_follow(
    api_key: str = Header(..., alias="api-key"),
    user_id: int = Path(..., ge=1),
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

        following = await get_user_by_id(db, user_id)
        if not following or following.id == user.id:
            return api_error(
                error_type="not_found",
                error_message="User not found or you try to follow yourself",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        follow = await get_follow_by_users_id(db, user.id, user_id)
        if follow:
            return api_error(
                error_type="follow_already_exists",
                error_message="You are already following this user",
                status_code=status.HTTP_409_CONFLICT,
            )

        follow = Follow(follower_id=user.id, following_id=following.id)

        db.add(follow)

        return TweetDeleteLikeFollowResponse(result=True)

    except Exception as exc:
        return api_error(
            error_type="server_error",
            error_message=str(exc),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.delete(
    "/users/{user_id}/follow",
    response_model=TweetDeleteLikeFollowResponse,
    responses={
        400: {RESPONSE_MODEL: ErrorResponse},
        401: {RESPONSE_MODEL: ErrorResponse},
        413: {RESPONSE_MODEL: ErrorResponse},
    },
    summary="Remove follow a user",
    description="Remove follow a user by user ID",
    tags=[TAG],
)
async def delete_follow(
    api_key: str = Header(..., alias="api-key"),
    user_id: int = Path(..., ge=1),
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

        follow = await get_follow_by_users_id(db, user.id, user_id)
        if not follow:
            return api_error(
                error_type="not_found",
                error_message="Follow not found",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        await db.delete(follow)

        return TweetDeleteLikeFollowResponse(result=True)

    except Exception as exc:
        return api_error(
            error_type="server_error",
            error_message=str(exc),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.get(
    "/users/me",
    response_model=UserResponse,
    responses={
        400: {RESPONSE_MODEL: ErrorResponse},
        401: {RESPONSE_MODEL: ErrorResponse},
        500: {RESPONSE_MODEL: ErrorResponse},
    },
    summary="Get current user profile",
    description="Returns detailed profile information "
    "including followers and following",
    tags=[TAG],
)
async def get_current_user_profile(
    api_key: str = Header(..., alias="api-key"), db: AsyncSession = Depends(get_db)
):
    try:
        user = await db.execute(
            select(User)
            .options(
                selectinload(User.followers).joinedload(Follow.follower),
                selectinload(User.following).joinedload(Follow.following),
            )
            .where(User.api_key == api_key)
        )
        user = user.scalar_one_or_none()
        if not user:
            return api_error(
                error_type="authentication_error",
                error_message="Invalid API key",
                status_code=status.HTTP_401_UNAUTHORIZED,
            )

        formatted_user = format_user(user)

        return {"result": True, "user": formatted_user}

    except Exception as exc:
        return api_error(
            error_type="server_error",
            error_message=str(exc),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.get(
    "/users/{user_id}",
    response_model=UserResponse,
    responses={
        400: {RESPONSE_MODEL: ErrorResponse},
        401: {RESPONSE_MODEL: ErrorResponse},
        500: {RESPONSE_MODEL: ErrorResponse},
    },
    summary="Get any user profile",
    description="Returns detailed profile information "
    "including followers and following by user ID",
    tags=[TAG],
)
async def get_any_user_profile(
    user_id: int = Path(..., ge=1), db: AsyncSession = Depends(get_db)
):
    try:
        user = await db.execute(
            select(User)
            .options(
                selectinload(User.followers).joinedload(Follow.follower),
                selectinload(User.following).joinedload(Follow.following),
            )
            .where(User.id == user_id)
        )
        user = user.scalar_one_or_none()
        if not user:
            return api_error(
                error_type="not_found",
                error_message="User not found",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        formatted_user = format_user(user)

        return {"result": True, "user": formatted_user}

    except Exception as exc:
        return api_error(
            error_type="server_error",
            error_message=str(exc),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
