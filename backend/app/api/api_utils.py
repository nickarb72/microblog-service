from typing import Dict, List

from fastapi.responses import JSONResponse

from backend.app.db.models import Tweet, User
from backend.app.schemas.tweet import ErrorResponse


def api_error(
    error_type: str, error_message: str, status_code: int = 400
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=ErrorResponse(
            result=False, error_type=error_type, error_message=error_message
        ).model_dump(),
    )


def format_tweets(tweets: List[Tweet]) -> List:
    formatted_tweets = []
    for tweet in tweets:
        formatted_tweets.append(
            {
                "id": tweet.id,
                "content": tweet.content,
                "attachments": [media.url for media in tweet.media],
                "author": {"id": tweet.author.id, "name": tweet.author.name},
                "likes": [
                    {"user_id": like.user.id, "name": like.user.name}
                    for like in tweet.likes
                ],
            }
        )

    return formatted_tweets


def format_user(user: User) -> Dict:
    formatted_user = {
        "id": user.id,
        "name": user.name,
        "followers": [
            {"id": follow.follower.id, "name": follow.follower.name}
            for follow in user.followers
        ],
        "following": [
            {"id": follow.following.id, "name": follow.following.name}
            for follow in user.following
        ],
    }

    return formatted_user
