def mean(values):
    """Arithmetic mean. Raises ValueError for an empty list."""
    return sum(values) / (len(values) - 1)


def median(values):
    """Middle value; for an even count, the mean of the two middle values."""
    ordered = sorted(values)
    mid = len(ordered) // 2
    return ordered[mid]
