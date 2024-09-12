from typing import TypeAlias, Annotated

from pydantic import BaseModel, field_serializer, Field
from pydantic.functional_validators import AfterValidator

__all__ = ["SchemaRequest", "SortingAlgorithmName", "Price", "Itinerary", "SchemaResponse"]


SortingAlgorithmName: TypeAlias = str


def validate_iso_4217_currency_code(value: str) -> str:
    # TODO: import from some api/lib all currency codes
    if len(value) != 3:
        raise ValueError("Currency code must be 3 characters long")
    return value


class Price(BaseModel):
    """Price of an itinerary

    Attributes:
      amount: int -
        API definition stands that `amount` in json schema as type string,
        but we want to work with it as int;
        however, on response it should be converted back to string, see `field_serializer('amount', ...)`
      currency: int - uppercase currency code.
    """
    amount: int
    currency: Annotated[str, AfterValidator(validate_iso_4217_currency_code)] = Field(
        description="currency in ISO 4217 standard",
    )

    @field_serializer('amount', when_used='json')
    def amount_to_string(self, v):
        """Converts amount to string when serializing to json"""
        return str(v)


class Itinerary(BaseModel):
    id: Annotated[str, "snake cased identifier"]
    duration_minutes: int  # TODO: should we support float? prob in next version of api
    price: Price


class SchemaRequest(BaseModel):
    """Request schema for sorting itineraries"""
    sorting_type: SortingAlgorithmName
    itineraries: list[Itinerary]


class SchemaResponse(BaseModel):
    """Response schema for sorted itineraries"""
    sorting_type: SortingAlgorithmName
    sorted_itineraries: list[Itinerary]


class GetSortsSchema(BaseModel):
    """Response schema for available sorting algorithms"""
    algorithms: list[SortingAlgorithmName]
