from decimal import Decimal
from typing import Protocol


class AccountRepository(Protocol):
    def get_balance(self, account_id: str) -> Decimal: ...


class InMemoryAccountRepository:
    def get_balance(self, account_id: str) -> Decimal:
        return Decimal("1500.00")


class AccountService:
    def __init__(self, repository: AccountRepository):
        self.repository = repository

    def get_balance(self, account_id: str) -> Decimal:
        return self.repository.get_balance(account_id)


repository = InMemoryAccountRepository()
service = AccountService(repository)

balance = service.get_balance("ACC1001")

print(f"Account balance: SAR {balance}")
