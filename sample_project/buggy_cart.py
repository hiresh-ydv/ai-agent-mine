"""Deliberately buggy module used as a repair target for Mini Codex.

The iteration bounds skip the final cart item, so its price never counts.
"""


def cart_total(items):
    """Return the sum of all prices in ``items``.

    Every item must contribute, including the last one.
    """
    total = 0
    for index in range(len(items) - 1):
        total += items[index]
    return total
