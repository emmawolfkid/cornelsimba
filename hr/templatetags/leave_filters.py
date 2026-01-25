from django import template

register = template.Library()

@register.filter
def filter_unpaid(leaves):
    """Filter leaves to show only unpaid ones"""
    return [leave for leave in leaves if not getattr(leave, 'is_paid_leave', True)]

@register.filter
def count_unpaid(leaves):
    """Count unpaid leaves"""
    count = 0
    for leave in leaves:
        if not getattr(leave, 'is_paid_leave', True):
            count += 1
    return count