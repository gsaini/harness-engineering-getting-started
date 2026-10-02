import pytest

from src.stats import mean, median


def test_mean():
    assert mean([2, 4, 6]) == 4


def test_mean_of_empty_list_raises():
    with pytest.raises(ValueError):
        mean([])


def test_median_odd_count():
    assert median([3, 1, 2]) == 2


def test_median_even_count():
    assert median([4, 1, 3, 2]) == 2.5
