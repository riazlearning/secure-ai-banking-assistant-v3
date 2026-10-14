import asyncio
import time


async def get_balance() -> str:
    await asyncio.sleep(2)
    return "SAR 1500"


async def get_transactions() -> str:
    await asyncio.sleep(3)
    return "5 transactions"


async def sequential() -> None:
    start = time.perf_counter()

    balance = await get_balance()
    transactions = await get_transactions()

    print("Sequential:", balance, transactions)
    print(f"Time: {time.perf_counter() - start:.2f}s")


async def concurrent() -> None:
    start = time.perf_counter()

    balance, transactions = await asyncio.gather(
        get_balance(),
        get_transactions(),
    )

    print("Concurrent:", balance, transactions)
    print(f"Time: {time.perf_counter() - start:.2f}s")


async def main() -> None:
    await sequential()
    await concurrent()


asyncio.run(main())
