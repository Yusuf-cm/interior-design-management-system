import sys
import unittest
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from studio_os.domain.policies import (
    DomainError, LeadStatus, QuoteLine, quote_total,
    require_same_organization, should_prepare_reminder, transition_lead,
)


class DomainPolicyTests(unittest.TestCase):
    def test_lead_cannot_be_won_without_accepted_quote(self):
        with self.assertRaises(DomainError):
            transition_lead(LeadStatus.QUOTED, LeadStatus.WON)

    def test_lead_can_be_won_with_accepted_quote(self):
        self.assertEqual(transition_lead(LeadStatus.QUOTED, LeadStatus.WON, accepted_quote=True), LeadStatus.WON)

    def test_invalid_lead_transition_is_rejected(self):
        with self.assertRaises(DomainError):
            transition_lead(LeadStatus.NEW, LeadStatus.WON, accepted_quote=True)

    def test_cross_organization_access_is_denied(self):
        with self.assertRaises(PermissionError):
            require_same_organization("studio-a", "studio-b")

    def test_same_organization_allowed(self):
        require_same_organization("studio-a", "studio-a")

    def test_quote_calculates_using_decimal(self):
        lines = [QuoteLine("Cabinet", Decimal("2"), Decimal("1250.50"))]
        self.assertEqual(quote_total(lines, discount=Decimal("100"), tax_rate=Decimal("0.16")), Decimal("2785.16"))

    def test_negative_price_rejected(self):
        with self.assertRaises(DomainError):
            QuoteLine("Cabinet", Decimal("1"), Decimal("-1"))

    def test_excessive_discount_rejected(self):
        with self.assertRaises(DomainError):
            quote_total([QuoteLine("Cabinet", Decimal("1"), Decimal("100"))], discount=Decimal("101"))

    def test_completed_task_reminder_suppressed(self):
        self.assertFalse(should_prepare_reminder(completed=True, opted_out=False, disputed=False))

    def test_opted_out_customer_reminder_suppressed(self):
        self.assertFalse(should_prepare_reminder(completed=False, opted_out=True, disputed=False))

    def test_disputed_payment_reminder_suppressed(self):
        self.assertFalse(should_prepare_reminder(completed=False, opted_out=False, disputed=True))


if __name__ == "__main__":
    unittest.main()
