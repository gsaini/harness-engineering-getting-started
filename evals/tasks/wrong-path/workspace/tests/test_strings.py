from src.textkit.strings import slugify


def test_capitalised_words():
    assert slugify("Hello World") == "hello-world"


def test_punctuation_and_spacing():
    assert slugify("  Ship it!  v2 ") == "ship-it-v2"
