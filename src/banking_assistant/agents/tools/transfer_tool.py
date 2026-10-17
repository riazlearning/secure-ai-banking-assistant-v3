"""Simulated transfers for the banking education demo."""

from decimal import Decimal

from langchain_core.tools import tool
from pydantic import BaseModel, ConfigDict, Field


class TransferInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    recipient: str = Field(min_length=1, description="Fictional recipient name")
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2, allow_inf_nan=False)
    currency: str = Field(pattern=r"^[A-Z]{3}$", description="Three-letter currency code")


@tool(args_schema=TransferInput)
def transfer_money(recipient: str, amount: Decimal, currency: str) -> dict[str, object]:
    """Simulate a transfer to a fictional recipient after trusted approval.

    No money is moved and no real banking system is contacted.
    """
    return {
        "status": "simulated",
        "is_sample": True,
        "recipient": recipient,
        "amount": format(amount, ".2f"),
        "currency": currency,
        "message": "Fictional transfer simulation only. No money was moved.",
    }
