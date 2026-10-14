class BankingConnection:
    def __enter__(self) -> "BankingConnection":
        print("Opening banking connection")
        return self

    def execute(self, query: str) -> None:
        print(f"Executing: {query}")

    def __exit__(
        self,
        exc_type: object,
        exc_value: object,
        traceback: object,
    ) -> None:
        print("Closing banking connection")


def main() -> None:
    with BankingConnection() as connection:
        connection.execute("SELECT balance FROM accounts")

    print("Request completed")


if __name__ == "__main__":
    main()
