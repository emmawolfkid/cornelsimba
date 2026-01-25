# cornelsimba/finance/templatetags/finance_filters.py
from django import template

register = template.Library()

@register.filter(name='subtract')
def subtract(value, arg):
    """Subtract the argument from the value."""
    try:
        return float(value) - float(arg)
    except (ValueError, TypeError):
        try:
            return value - arg
        except:
            return 0

@register.filter(name='abs')
def absolute(value):
    """Return absolute value."""
    try:
        return abs(float(value))
    except (ValueError, TypeError):
        try:
            return abs(value)
        except:
            return value

@register.filter(name='multiply')
def multiply(value, arg):
    """Multiply value by arg."""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        try:
            return value * arg
        except:
            return 0

@register.filter(name='divide')
def divide(value, arg):
    """Divide value by arg."""
    try:
        return float(value) / float(arg)
    except (ValueError, TypeError, ZeroDivisionError):
        return 0