class BankingError(Exception):
    """Base exception for banking business errors."""


class TransferRejectedError(BankingError):
    """Raised when a transfer violates a banking business rule."""

    def __init__(self, message: str):
        super().__init__(message)
