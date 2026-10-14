from decimal import Decimal

from pydantic import BaseModel, ConfigDict, ValidationError


class TransferRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    amount: Decimal
    currency: str


def main() -> None:
    print("TEST 1: Python dictionary with string amount")

    try:
        TransferRequest.model_validate(
            {
                "amount": "500.00",
                "currency": "SAR",
            }
        )
    except ValidationError:
        print("Rejected: Expected Decimal instance")

    print("\nTEST 2: Python dictionary with Decimal amount")

    request = TransferRequest.model_validate(
        {
            "amount": Decimal("500.00"),
            "currency": "SAR",
        }
    )

    print(f"Accepted: {request.amount}")

    print("\nTEST 3: JSON string with decimal amount")

    request_from_json = TransferRequest.model_validate_json(
        '{"amount": "500.00", "currency": "SAR"}'
    )

    print(f"Accepted JSON: {request_from_json.amount}")
    print(f"Type: {type(request_from_json.amount).__name__}")


if __name__ == "__main__":
    main()
