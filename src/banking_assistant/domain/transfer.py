from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class TransferDetails:
    source_account: str
    destination_account: str
    amount: Decimal
    currency: str
