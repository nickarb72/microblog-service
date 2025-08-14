from typing import List, Optional

from fastapi import UploadFile, File
from pydantic import BaseModel, Field, RootModel


class TweetCreateRequest(BaseModel):
    """Schema for creating tweet"""
    tweet_data: str = Field(
        ...,
        min_length=1,
        max_length=280,
        example="Example for text of tweet",
        description="Text of tweet (1-280 symbols)"
    )
    tweet_media_ids: Optional[List[int]] = Field(
        default=None,
        example=[1, 2, 3],
        description="List of media files ID (optionally)"
    )


class TweetCreateResponse(BaseModel):
    """Schema of successful response"""
    result: bool = Field(..., example=True)
    tweet_id: int = Field(..., example=42)


class ErrorResponse(BaseModel):
    """Error response schema for every model"""
    result: bool = Field(..., example=False)
    error_type: str = Field(..., example="validation_error")
    error_message: str = Field(..., example="Discription of occured error")


class MediaUploadResponse(BaseModel):
    """Response schema for successful media upload"""
    result: bool = Field(..., example=True)
    media_id: int = Field(..., example=42)


class MediaFileForm:
    """File upload form schema for Swagger docs"""
    def __init__(
        self,
        file: UploadFile = File(..., description="Image file (JPEG, PNG) max 5MB")
    ):
        self.file = file


class TweetDeleteLikeFollowResponse(BaseModel):
    """Response schema for successful deleting tweet or
    successful Like on/off or successful Follow on/off"""
    result: bool = Field(..., example=True)


class TweetAuthor(BaseModel):
    id: int = Field(..., example=42)
    name: str = Field(..., example="John Doe")


class TweetLike(BaseModel):
    user_id: int = Field(..., example=11)
    name: str = Field(..., example="Alice Smith")


class TweetAttachment(RootModel[str]):
    root: str = Field(..., example="uploads/1d4cf242-c676-48a9-95f1-5296103f6097.jpg")


class TweetResponse(BaseModel):
    id: int = Field(..., example=9)
    content: str = Field(..., example="Hello world!", max_length=280)
    attachments: List[TweetAttachment] = Field(
        default_factory=list,
        example=[
            "uploads/9d4cf242-c676-48a9-95f1-5296103f6097.jpg",
            "uploads/8fe38885-4591-41c2-ae97-2e3bf1b26cd9.jpg",
            "uploads/a82e6102-f4de-45c3-8d08-32ad3b253312.jpg"
        ]
    )
    author: TweetAuthor
    likes: List[TweetLike] = Field(default_factory=list)


class TweetsFeedResponse(BaseModel):
    """Response schema for successful getting tweet feed"""
    result: bool = Field(..., example=True)
    tweets: List[TweetResponse] = Field(default_factory=list)