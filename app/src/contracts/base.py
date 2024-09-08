from pydantic import BaseModel


class ErrorResponse(BaseModel):
    reason: str
    error: str
