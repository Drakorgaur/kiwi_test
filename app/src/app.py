from typing import TypeVar

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from src._logging import configure_logging
from src.contracts.base import ErrorResponse
from src.contracts.sort_itineraries import (
    SchemaRequest as SortItinerariesSchemaRequest, SortingAlgorithmName,
    SchemaResponse as SortItinerariesSchemaResponse, GetSortsSchema
)
from src.exceptions import AppBadRequest, AppServiceUnavailable
from src.sorts import sort_itineraries
from src.sorts.base import get_sort_algorithms

AnyBadRequest = TypeVar("AnyBadRequest", bound=AppBadRequest)
AnyServiceUnavailable = TypeVar("AnyServiceUnavailable", bound=AppServiceUnavailable)

app = FastAPI()


@app.on_event("startup")
async def startup():
    """Configure logging on startup.

    The problem is that uvicorn should be run with CLI client.
    That blocks application to set uvicorn loggers to output a valid json-like log.
    So the application corrects loggers that are used by uvicorn processes to set new handlers and formatters.
    """
    configure_logging()


@app.exception_handler(AppBadRequest)
async def _(_, exc: AnyBadRequest):
    """Handle AppBadRequest exception.

    Any request that has unhandled exception bounded to `AppBadRequest`
    is processed here to return a proper response.
    
    Attributes:
        _: Request
        exc: CurrencyUnavailableException | SortAlgorithmIsUnknown
    """
    return JSONResponse(
        status_code=400,
        content={
            "reason": "Bad Request",
            "error": str(exc)
        }
    )


@app.exception_handler(AppServiceUnavailable)
async def _(_, exc: AnyServiceUnavailable):
    """ Handle AppServiceUnavailable exception.

    Any request that has unhandled exception bounded to `AppServiceUnavailable`
    is processed here to return a proper response.

    Attributes:
        _: Request
        exc: CurrencyUnavailableException | ExternalAPIError
    """
    return JSONResponse(
        status_code=503,
        content={
            "reason": "Service Unavailable",
            "error": str(exc)
        }
    )


@app.get("/healthz")
async def health() -> dict[str, str]:
    """HTTP GET /healthz handler.

    Handler is responsible for returning the health status of the service.
    Used in health checks.
    """
    return {"status": "ok"}


@app.get("/sorts", response_model=GetSortsSchema, tags=["sorts"], summary="Get available sorting algorithms")
async def sorts() -> GetSortsSchema:
    """HTTP GET /sorts handler.

    Handler is responsible for returning available sorting algorithms that can be used to sort itineraries.

    :return: GetSortsSchema
    """
    return GetSortsSchema(algorithms=list(get_sort_algorithms()))


@app.post(
    "/sort_itineraries",
    response_model=SortItinerariesSchemaResponse,
    responses={400: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
    tags=["itineraries", "sorts"],
    summary="Sort itineraries by given algorithm",
    description="available algorithms can be found at `/sorts`",
)  # maybe should be versioned as /v1/
async def sort_itineraries_handler(data: SortItinerariesSchemaRequest) -> SortItinerariesSchemaResponse:
    """HTTP POST /sort_itineraries handler.

    Handler is responsible for sorting itineraries by given algorithm.

    Input validation:
        Part of the validation process is done by pydantic, it validates the schema.
        Then validated that algorithm requested is available.
        During the sort is also checks that currency code is valid.

    Algorithm:
        ::: v1 12.09.2024 ::::
        Time complexity is the same as for PowerSort / TimSort - O(n * log(n)).
        Sort is done with python built-in `sorted` function and `key=` parameter.
    """
    algorithm: SortingAlgorithmName = data.sorting_type
    return SortItinerariesSchemaResponse(
        sorting_type=algorithm,
        sorted_itineraries=await sort_itineraries(algorithm, data.itineraries)
    )


if __name__ == "__main__":
    """Debug mode entry point."""
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
