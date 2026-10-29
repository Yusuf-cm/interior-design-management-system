from decimal import Decimal
from django import template

register = template.Library()


@register.filter
def decimal_money(value):
    return format(Decimal(str(value)), ',.2f')
