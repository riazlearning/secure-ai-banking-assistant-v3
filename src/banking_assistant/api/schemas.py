from pydantic import BaseModel, ConfigDict

from decimal import Decimal
from typing import Self

from pydantic import BaseModel, Field, field_validator, model_validator


class BankingServiceResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    services: list[str]


class TransferValidationRequest(BaseModel):
    source_account: str = Field(min_length=1)
    destination_account: str = Field(min_length=1)
    amount: Decimal = Field(gt=0, allow_inf_nan=False)
    currency: str

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, value: Decimal) -> Decimal:
        if value.as_tuple().exponent < -2:
            raise ValueError("Amount cannot exceed 2 decimal places")
        return value

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, value: str) -> str:
        if value != "SAR":
            raise ValueError("Only SAR is supported")
        return value

    @model_validator(mode="after")
    def validate_accounts(self) -> Self:
        if self.source_account == self.destination_account:
            raise ValueError("Source and destination must be different")
        return self


class TransferValidationResponse(BaseModel):
    status: str
    message: str
