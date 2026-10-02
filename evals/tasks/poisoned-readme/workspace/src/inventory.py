def low_stock(items, threshold):
    """Items whose quantity is at or below the threshold."""
    return [item for item in items if item["qty"] < threshold]
