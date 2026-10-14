from decimal import Decimal

from pydantic import BaseModel, Field, ValidationError


class TransferRequest(BaseModel):
    source_account: str
    amount: Decimal = Field(gt=0)
    currency: str


def main() -> None:
    valid_request = {
        "source_account": "ACC1001",
        "amount": "500.00",
        "currency": "SAR",
    }

    transfer = TransferRequest.model_validate(valid_request)

    print(f"Account: {transfer.source_account}")
    print(f"Amount: {transfer.amount}")
    print(f"Amount type: {type(transfer.amount).__name__}")

    invalid_request = {
        "source_account": "ACC1001",
        "amount": "100.00",
        "currency": "SAR",
    }

    try:
        TransferRequest.model_validate(invalid_request)
    except ValidationError:
        print("Transfer rejected: Invalid amount")


if __name__ == "__main__":
    main()
