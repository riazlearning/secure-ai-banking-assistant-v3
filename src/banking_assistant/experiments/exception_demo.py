class BankingError(Exception):
    """Base exception for banking errors."""


class AccountNotFoundError(BankingError):
    """Raised when an account does not exist."""


def get_account_balance(account_id: str) -> int:
    if account_id != "ACC1001":
        raise AccountNotFoundError(f"Account {account_id} not found")

    return 1500


def main() -> None:
    try:
        balance = get_account_balance("ACC1001")
        print(f"Balance: SAR {balance}")

    except AccountNotFoundError:
        print("Unable to retrieve the requested account.")

    finally:
        print("Banking request processing completed.")


if __name__ == "__main__":
    main()
