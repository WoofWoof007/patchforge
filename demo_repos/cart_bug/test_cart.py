from cart import apply_discount, total


def test_no_discount():
    assert apply_discount(100, 0) == 100


def test_total():
    assert total([10, 20]) == 30