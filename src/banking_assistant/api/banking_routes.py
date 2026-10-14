from typing import Annotated

from fastapi import APIRouter, Depends

from banking_assistant.api.banking_controller import BankingController
from banking_assistant.api.dependencies import get_banking_controller
from banking_assistant.api.schemas import BankingServiceResponse
from banking_assistant.api.schemas import (
    TransferValidationRequest,
    TransferValidationResponse,
)

router = APIRouter(
    prefix="/api/v1/banking",
    tags=["Banking"],
)


@router.get("/services", response_model=BankingServiceResponse)
def get_available_services(
    controller: Annotated[
        BankingController,
        Depends(get_banking_controller),
    ],
) -> BankingServiceResponse:
    services = controller.get_available_services()
    return BankingServiceResponse(services=services, pwd="This is a test password")


@router.post(
    "/transfers/validate",
    response_model=TransferValidationResponse,
)
def validate_transfer(
    request: TransferValidationRequest,
    controller: Annotated[
        BankingController,
        Depends(get_banking_controller),
    ],
) -> TransferValidationResponse:
    validated = controller.validate_transfer_request(request)
    if validated:
        return TransferValidationResponse(
            status="accepted",
            message="Request format validated. No transfer executed.",
        )

    return TransferValidationResponse(
        status="rejected",
        message="Request validation failed.",
    )
