from buggy_discount import apply_discount


def test_twenty_percent_off_100():
    assert apply_discount(100, 20) == 80.0


def test_ten_percent_off_50():
    assert apply_discount(50, 10) == 45.0


def test_zero_discount_leaves_price():
    assert apply_discount(30, 0) == 30.0


def test_hundred_percent_discount_is_free():
    assert apply_discount(30, 100) == 0.0
