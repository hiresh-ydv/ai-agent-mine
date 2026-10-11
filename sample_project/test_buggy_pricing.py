from buggy_pricing import is_eligible_for_free_shipping


def test_exactly_at_threshold_qualifies():
    assert is_eligible_for_free_shipping(50.0, 50.0) is True


def test_just_below_threshold_does_not_qualify():
    assert is_eligible_for_free_shipping(49.99, 50.0) is False


def test_above_threshold_qualifies():
    assert is_eligible_for_free_shipping(100.0, 50.0) is True
