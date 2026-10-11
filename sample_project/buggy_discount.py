"""Deliberately buggy module used as a repair target for Mini Codex.

The discount percentage is subtracted as if it were a currency amount instead
of first being converted to a fraction of the price.
"""


def apply_discount(price, discount_percent):
    """Return the price after applying ``discount_percent`` percent off.

    Example: ``apply_discount(100, 20)`` should return ``80.0``.
    """
    return price - discount_percent
