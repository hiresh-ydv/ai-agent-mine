from buggy_cart import cart_total


def test_three_items_all_count():
    assert cart_total([10, 20, 30]) == 60


def test_empty_cart_is_zero():
    assert cart_total([]) == 0


def test_single_item_counts():
    assert cart_total([5]) == 5


def test_two_float_items():
    assert cart_total([1.5, 2.5]) == 4.0
