from typing import List, Optional

from fastapi import UploadFile, File
from pydantic import BaseModel, Field


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