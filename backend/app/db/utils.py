from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from backend.app.db.models import User


async def get_user_by_api_key(db: AsyncSession, api_key: str) -> Optional[User]:
    """Get user from DB by API key"""
    result = await db.execute(
        select(User).where(User.api_key == api_key)
    )
    return result.scalar_one_or_none()