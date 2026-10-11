from buggy_discount import final_price


def test_twenty_percent_off_100():
    assert final_price(100, 20) == 80.0


def test_twentyfive_percent_off_200():
    assert final_price(200, 25) == 150.0


def test_no_discount():
    assert final_price(50, 0) == 50.0


def test_full_discount_is_free():
    assert final_price(40, 100) == 0.0
