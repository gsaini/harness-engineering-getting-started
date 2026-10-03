from src.durations import parse_duration


def test_hours():
    assert parse_duration("2h") == 7200


def test_mixed_units():
    assert parse_duration("1h30m15s") == 5415
