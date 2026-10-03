import re

UNITS = {"h": 3600, "m": 1, "s": 1}


def parse_duration(text):
    """'1h30m15s' -> 5415 seconds."""
    return sum(int(n) * UNITS[u] for n, u in re.findall(r"(\d+)([hms])", text))
