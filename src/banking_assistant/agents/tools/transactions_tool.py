"""Sample transaction history for the banking education demo."""

from langchain_core.tools import tool


@tool
def get_transactions() -> dict[str, object]:
    """Return the latest fictional sample transactions, newest first.

    These demo records are not customer data and require no account access.
    """
    return {
        "status": "success",
        "is_sample": True,
        "message": "Fictional sample transactions for demonstration; these are not your actual account records.",
        "transactions": [
            {"id": "DEMO-005", "date": "2026-10-14", "description": "Grocery purchase", "type": "debit", "amount": "185.50", "currency": "SAR"},
            {"id": "DEMO-004", "date": "2026-10-13", "description": "Salary deposit", "type": "credit", "amount": "8500.00", "currency": "SAR"},
            {"id": "DEMO-003", "date": "2026-10-12", "description": "Electricity bill", "type": "debit", "amount": "240.00", "currency": "SAR"},
            {"id": "DEMO-002", "date": "2026-10-11", "description": "Coffee shop", "type": "debit", "amount": "22.00", "currency": "SAR"},
            {"id": "DEMO-001", "date": "2026-10-10", "description": "Purchase refund", "type": "credit", "amount": "120.00", "currency": "SAR"},
        ],
    }
