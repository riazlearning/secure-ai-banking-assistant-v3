from banking_assistant.services.banking_service import BankingService


class BankingController:
    def __init__(self, banking_service: BankingService):
        self.banking_service = banking_service

    def get_available_services(self) -> list[str]:
        return self.banking_service.get_available_services()
