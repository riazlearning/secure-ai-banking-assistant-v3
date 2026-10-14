class AccountServiceUnavailableError(Exception):
    pass


class CoreBankingClient:
    def get_balance(self, account_id: str) -> int:
        raise ConnectionError("Core banking connection refused")


class AccountService:
    def __init__(self, client: CoreBankingClient):
        self.client = client

    def get_balance(self, account_id: str) -> int:
        try:
            return self.client.get_balance(account_id)
        except ConnectionError as exc:
            raise AccountServiceUnavailableError(
                "Account service is temporarily unavailable"
            ) from exc


class AccountController:
    def __init__(self, service: AccountService):
        self.service = service

    def get_balance(self, account_id: str) -> dict[str, str | int]:
        try:
            balance = self.service.get_balance(account_id)
            return {"status": "success", "balance": balance}
        except AccountServiceUnavailableError:
            return {
                "status": "error",
                "message": "Unable to retrieve balance right now",
            }


controller = AccountController(AccountService(CoreBankingClient()))

print(controller.get_balance("ACC1001"))
