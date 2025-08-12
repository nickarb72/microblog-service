from fastapi import HTTPException
from fastapi.responses import JSONResponse

from backend.app.schemas.tweet import ErrorResponse


def api_error(
    error_type: str,
    error_message: str,
    status_code: int = 400
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=ErrorResponse(
            result=False,
            error_type=error_type,
            error_message=error_message
        ).model_dump()
    )