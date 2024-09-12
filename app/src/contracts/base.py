from pydantic import BaseModel


class ErrorResponse(BaseModel):
    """Error response schema

    This class is used to represent error response from the API.
    Response is counted as an error if status code is not 2xx.
    """
    reason: str
    error: str
