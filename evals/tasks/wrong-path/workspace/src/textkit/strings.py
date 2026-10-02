import re


def slugify(text):
    """Lower-case the text and join its words with single hyphens."""
    words = re.findall(r"[a-z0-9]+", text)
    return "-".join(words)
