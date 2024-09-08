from fastapi import FastAPI
from fastapi.responses import JSONResponse

from src._logging import configure_logging
from src.contracts.base import ErrorResponse
from src.contracts.sort_itineraries import (
    SchemaRequest as SortItinerariesSchemaRequest, SortingAlgorithmName, SchemaResponse as SortItinerariesSchemaResponse
)
from src.currency.apis.exceptions import ExternalAPIError
from src.currency.exceptions import CurrencyUnavailableException
from src.exceptions import AppBadRequest, AppServiceUnavailable
from src.sorts import sort_itineraries, SortAlgorithmIsUnknown
from src.sorts.base import get_sort_algorithms

app = FastAPI()


@app.on_event("startup")
async def startup():
    configure_logging()


@app.exception_handler(AppBadRequest)
async def _(_, exc: CurrencyUnavailableException | SortAlgorithmIsUnknown):
    return JSONResponse(
        status_code=400,
        content={
            "reason": "Bad Request",
            "error": str(exc)
        }
    )


@app.exception_handler(AppServiceUnavailable)
async def _(_, exc: CurrencyUnavailableException | ExternalAPIError):
    return JSONResponse(
        status_code=503,
        content={
            "reason": "Service Unavailable",
            "error": str(exc)
        }
    )


@app.get("/healthz")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/sorts")
async def sorts() -> dict[str, list[str]]:
    return {"algorithms": list(get_sort_algorithms())}


@app.post(
    "/sort_itineraries",
    response_model=SortItinerariesSchemaResponse,
    responses={400: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
    tags=["itineraries"],
    summary="Sort itineraries by given algorithm",
    description="available algorithms can be found at `/sorts`",
)  # maybe should be versioned as /v1/
async def sort_itineraries_handler(data: SortItinerariesSchemaRequest) -> SortItinerariesSchemaResponse:
    algorithm: SortingAlgorithmName = data.sorting_type
    return SortItinerariesSchemaResponse(
        sorting_type=algorithm,
        sorted_itineraries=await sort_itineraries(algorithm, data.itineraries)
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
