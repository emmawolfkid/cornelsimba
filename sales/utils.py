# cornelsimba/sales/utils.py
def format_currency(amount, currency='Tsh'):
    """Format amount with appropriate currency symbol"""
    if currency == 'Tsh':
        return f"Tsh {amount:,.2f}"
    elif currency == 'USD':
        return f"${amount:,.2f}"
    elif currency == 'EUR':
        return f"€{amount:,.2f}"
    else:
        return f"{amount:,.2f}"

def convert_to_tsh(amount, from_currency='USD', exchange_rate=2500):
    """Convert foreign currency to Tsh"""
    if from_currency == 'Tsh':
        return amount
    return amount * exchange_rate

def convert_from_tsh(amount, to_currency='USD', exchange_rate=2500):
    """Convert Tsh to foreign currency"""
    if to_currency == 'Tsh':
        return amount
    return amount / exchange_rate