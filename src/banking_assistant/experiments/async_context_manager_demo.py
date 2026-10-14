import asyncio
from types import TracebackType


class AsyncBankingConnection:
    async def __aenter__(self) -> "AsyncBankingConnection":
        print("Opening async banking connection")
        await asyncio.sleep(1)
        return self

    async def execute(self, query: str) -> None:
        print(f"Executing: {query}")
        await asyncio.sleep(1)

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        print("Closing async banking connection")
        await asyncio.sleep(1)


async def main() -> None:
    async with AsyncBankingConnection() as connection:
        await connection.execute("SELECT balance FROM accounts")

    print("Banking request completed")


if __name__ == "__main__":
    asyncio.run(main())
