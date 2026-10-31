"""Pure domain rules for Studio.OS. No database or network effects."""
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum


class DomainError(ValueError):
    pass


class LeadStatus(str, Enum):
    NEW = "NEW"
    CONTACTED = "CONTACTED"
    QUALIFIED = "QUALIFIED"
    CONSULTATION_BOOKED = "CONSULTATION_BOOKED"
    ASSESSED = "ASSESSED"
    QUOTED = "QUOTED"
    WON = "WON"
    LOST = "LOST"
    DORMANT = "DORMANT"


LEAD_TRANSITIONS = {
    LeadStatus.NEW: {LeadStatus.CONTACTED, LeadStatus.LOST, LeadStatus.DORMANT},
    LeadStatus.CONTACTED: {LeadStatus.QUALIFIED, LeadStatus.LOST, LeadStatus.DORMANT},
    LeadStatus.QUALIFIED: {LeadStatus.CONSULTATION_BOOKED, LeadStatus.LOST, LeadStatus.DORMANT},
    LeadStatus.CONSULTATION_BOOKED: {LeadStatus.ASSESSED, LeadStatus.LOST},
    LeadStatus.ASSESSED: {LeadStatus.QUOTED, LeadStatus.LOST},
    LeadStatus.QUOTED: {LeadStatus.WON, LeadStatus.LOST, LeadStatus.DORMANT},
    LeadStatus.DORMANT: {LeadStatus.CONTACTED, LeadStatus.LOST, LeadStatus.WON},
    LeadStatus.WON: set(),
    LeadStatus.LOST: set(),
}


def transition_lead(current: LeadStatus, target: LeadStatus, *, accepted_quote=False):
    if target not in LEAD_TRANSITIONS[current]:
        raise DomainError(f"Invalid lead transition: {current} -> {target}")
    if target == LeadStatus.WON and not accepted_quote:
        raise DomainError("A lead cannot be won without a recorded accepted quotation")
    return target


def require_same_organization(actor_org_id: str, resource_org_id: str):
    if not actor_org_id or not resource_org_id or actor_org_id != resource_org_id:
        raise PermissionError("Resource unavailable")


@dataclass(frozen=True)
class QuoteLine:
    description: str
    quantity: Decimal
    unit_price: Decimal

    def __post_init__(self):
        if not self.description.strip() or self.quantity <= 0 or self.unit_price < 0:
            raise DomainError("Quote line must have a description, positive quantity and nonnegative price")

    @property
    def total(self):
        return self.quantity * self.unit_price


def quote_total(lines, *, discount=Decimal("0"), tax_rate=Decimal("0")):
    if discount < 0 or tax_rate < 0:
        raise DomainError("Discount and tax rate must be nonnegative")
    subtotal = sum((line.total for line in lines), Decimal("0"))
    if discount > subtotal:
        raise DomainError("Discount exceeds subtotal")
    return ((subtotal - discount) * (Decimal("1") + tax_rate)).quantize(Decimal("0.01"))


def should_prepare_reminder(*, completed: bool, opted_out: bool, disputed: bool):
    return not (completed or opted_out or disputed)

