import unittest
from decimal import Decimal
from studio_os.domain.policies import DomainError
from studio_os.domain.pricing import calculate_estimate


class EstimatePricingTests(unittest.TestCase):
    def item(self, quantity="1", price="1"):
        return {"description": "Work", "quantity": Decimal(quantity), "unit_price": Decimal(price)}

    def test_round_each_line_half_up_before_subtotal(self):
        result = calculate_estimate([self.item("0.005"), self.item("0.005")])
        self.assertEqual(result["subtotal"], Decimal("0.02"))
        self.assertEqual(result["items"][0]["amount"], "0.01")

    def test_tax_rounds_half_up_after_discount(self):
        result = calculate_estimate([self.item(price="100.05")],
                                    discount=Decimal("100"), tax_rate=Decimal("0.1"))
        self.assertEqual(result["tax"], Decimal("0.01"))
        self.assertEqual(result["total"], Decimal("0.06"))

    def test_zero_price_and_full_discount(self):
        self.assertEqual(calculate_estimate([self.item(price="0")])["total"], Decimal("0"))
        self.assertEqual(calculate_estimate([self.item()], discount=Decimal("1"))["total"], Decimal("0"))

    def test_large_total_rejected(self):
        with self.assertRaises(DomainError):
            calculate_estimate([self.item("999999999", "9999999999.99")])

    def test_nonfinite_and_invalid_values_rejected(self):
        for item in [self.item("NaN"), self.item(price="Infinity"), self.item("0"), self.item(price="-1")]:
            with self.assertRaises(DomainError):
                calculate_estimate([item])
        for discount, tax in [("2", "0"), ("-1", "0"), ("0", "1.1"), ("NaN", "0")]:
            with self.assertRaises(DomainError):
                calculate_estimate([self.item()], Decimal(discount), Decimal(tax))

    def test_line_limit(self):
        for items in [[], [self.item()]*101]:
            with self.assertRaises(DomainError):
                calculate_estimate(items)
