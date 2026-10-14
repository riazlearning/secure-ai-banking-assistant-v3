from banking_assistant.services.banking_service import BankingService

from banking_assistant.api.schemas import TransferValidationRequest
from banking_assistant.domain.transfer import TransferDetails


class BankingController:
    def __init__(self, banking_service: BankingService):
        self.banking_service = banking_service

    def get_available_services(self) -> list[str]:
        return self.banking_service.get_available_services()

    def validate_transfer_request(
        self,
        request: TransferValidationRequest,
    ) -> bool:
        transfer = TransferDetails(
            source_account=request.source_account,
            destination_account=request.destination_account,
            amount=request.amount,
            currency=request.currency,
        )

        return self.banking_service.validate_transfer_request(transfer)
