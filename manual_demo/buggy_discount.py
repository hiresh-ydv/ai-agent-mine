"""A deliberately broken discount helper.

BUG: the discount percentage is subtracted as if it were a currency amount,
instead of being converted to a fraction of the price first.
"""


def final_price(price, discount_percent):
    """Return the price after applying ``discount_percent`` percent off.

    Example: ``final_price(100, 20)`` should return ``80.0``.
    """
    return price * (1 - discount_percent / 100)
