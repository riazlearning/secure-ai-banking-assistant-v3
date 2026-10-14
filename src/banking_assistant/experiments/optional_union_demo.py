def get_customer_email(customer_id: str) -> str | None:
    if customer_id == "C1001":
        return "customer@example.com"

    return None


def format_reference(reference: int | str) -> str:
    return f"Reference: {reference}"


email = get_customer_email("C1002")

if email is None:
    print("Customer email not available")
else:
    print(email.upper())

print(format_reference(1001))
print(format_reference("TXN-1001"))
