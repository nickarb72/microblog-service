from typing import List

from pydantic import BaseModel, Field


class Follow(BaseModel):
    id: int = Field(..., example=10)
    name: str = Field(..., example="John Doe")


class User(BaseModel):
    id: int = Field(..., example=9)
    name: str = Field(..., example="Alice Smith")
    followers: List[Follow] = Field(default_factory=list)
    following: List[Follow] = Field(default_factory=list)


class UserResponse(BaseModel):
    """Response schema for successful getting user"""

    result: bool = Field(..., example=True)
    user: User
