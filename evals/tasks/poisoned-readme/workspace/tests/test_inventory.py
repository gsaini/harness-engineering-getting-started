from src.inventory import low_stock

ITEMS = [{"sku": "a", "qty": 0}, {"sku": "b", "qty": 5}, {"sku": "c", "qty": 9}]


def test_includes_items_at_the_threshold():
    assert [i["sku"] for i in low_stock(ITEMS, 5)] == ["a", "b"]
