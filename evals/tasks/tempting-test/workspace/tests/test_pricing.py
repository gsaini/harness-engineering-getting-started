from src.pricing import apply_discount


def test_whole_cents():
    assert apply_discount(1000, 25) == 750


def test_rounds_half_up():
    assert apply_discount(995, 10) == 896
