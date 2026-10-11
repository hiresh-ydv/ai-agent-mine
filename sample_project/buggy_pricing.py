"""Deliberately buggy module used as a repair target for Mini Codex.

The free-shipping boundary uses an exclusive comparison, so a subtotal exactly
equal to the threshold is incorrectly rejected.
"""


def is_eligible_for_free_shipping(subtotal, threshold=50.0):
    """Return True when ``subtotal`` qualifies for free shipping.

    A subtotal exactly equal to ``threshold`` should qualify.
    """
    return subtotal > threshold
