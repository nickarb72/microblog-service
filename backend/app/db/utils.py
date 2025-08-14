from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from backend.app.db.models import User, Tweet, Like, Follow


async def get_user_by_api_key(db: AsyncSession, api_key: str) -> Optional[User]:
    """Get user from DB by API key"""
    result = await db.execute(
        select(User).where(User.api_key == api_key)
    )
    return result.scalar_one_or_none()


async def get_tweet_by_id(db: AsyncSession, tweet_id: int) -> Optional[Tweet]:
    """Get tweet from DB by tweet ID"""
    result = await db.execute(
        select(Tweet).where(Tweet.id == tweet_id)
    )
    return result.scalar_one_or_none()


async def get_like_by_tweet_and_user_id(db: AsyncSession, tweet_id: int, user_id: int) -> Optional[Like]:
    """Get like from DB by tweet ID"""
    result = await db.execute(
        select(Like).where(Like.tweet_id == tweet_id, Like.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
    """Get user from DB by user ID"""
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    return result.scalar_one_or_none()


async def get_follow_by_users_id(db: AsyncSession, follower_id: int, following_id: int) -> Optional[Follow]:
    """Get follow from DB by users ID"""
    result = await db.execute(
        select(Follow).where(Follow.follower_id == follower_id,
                             Follow.following_id == following_id))
    return result.scalar_one_or_none()