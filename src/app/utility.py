import re


def clear_url(url: str) -> str:
    """
    Removes trailing slashes and whitespace from a URL.
    """
    base_url = url.strip().rstrip("/")
    typo_match = re.match(r"^(https?://[^/:]+:\d+)[A-Za-z]+$", base_url)
    if typo_match:
        base_url = typo_match.group(1)

    return base_url
