"""Deterministic draft-estimate arithmetic. No tax rules or payment effects."""
from decimal import Decimal, ROUND_HALF_UP
from .policies import DomainError

CENT = Decimal("0.01")
MAX_MONEY = Decimal("9999999999999999.99")


def calculate_estimate(items, discount=Decimal("0"), tax_rate=Decimal("0")):
    if not items or len(items) > 100:
        raise DomainError("Supply between one and 100 estimate lines")
    if not discount.is_finite() or not tax_rate.is_finite() or discount < 0 or not 0 <= tax_rate <= 1:
        raise DomainError("Discount must be nonnegative and tax rate between zero and one")
    rows = []
    for item in items:
        quantity, price = item["quantity"], item["unit_price"]
        if not quantity.is_finite() or not price.is_finite() or quantity <= 0 or price < 0:
            raise DomainError("Quantity must be positive and price nonnegative")
        amount = (quantity * price).quantize(CENT, rounding=ROUND_HALF_UP)
        rows.append({"description": item["description"], "quantity": str(quantity),
                     "unit_price": str(price), "amount": str(amount)})
    subtotal = sum((Decimal(row["amount"]) for row in rows), Decimal("0.00"))
    if discount > subtotal:
        raise DomainError("Discount exceeds subtotal")
    tax = ((subtotal - discount) * tax_rate).quantize(CENT, rounding=ROUND_HALF_UP)
    total = (subtotal - discount + tax).quantize(CENT, rounding=ROUND_HALF_UP)
    if max(subtotal, total) > MAX_MONEY:
        raise DomainError("Estimate exceeds supported amount")
    return {"items": rows, "subtotal": subtotal, "discount": discount,
            "tax_rate": tax_rate, "tax": tax, "total": total}
