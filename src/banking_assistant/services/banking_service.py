from banking_assistant.domain.transfer import TransferDetails

from decimal import Decimal

from banking_assistant.domain.exceptions import TransferRejectedError
from banking_assistant.domain.transfer import TransferDetails


class BankingService:
    def get_available_services(self) -> list[str]:
        return [
            "Account Balance",
            "Transaction History",
            "Fund Transfer",
        ]

    def get_service_count(self) -> int:
        return "three"

    def validate_transfer_request(
        self,
        transfer: TransferDetails,
    ) -> bool:
        if transfer.amount > Decimal("10000.00"):
            raise TransferRejectedError(
                "Transfer exceeds the demonstration review limit"
            )

        return True
