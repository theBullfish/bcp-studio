from django import template

register = template.Library()


@register.filter
def cents(value):
    """Render integer cents as a dollar amount, e.g. 12345 -> 123.45"""
    try:
        return f"{int(value) / 100:,.2f}"
    except (TypeError, ValueError):
        return "0.00"


@register.filter
def dollars(value):
    """Whole-dollar version, e.g. 12345 -> 123"""
    try:
        return f"{int(value) / 100:,.0f}"
    except (TypeError, ValueError):
        return "0"
