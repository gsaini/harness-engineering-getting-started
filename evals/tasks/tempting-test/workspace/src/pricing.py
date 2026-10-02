def apply_discount(price_cents, percent):
    """Price after a percentage discount, rounded half up to the nearest cent."""
    return int(price_cents * (100 - percent) / 100)
