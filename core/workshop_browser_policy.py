from urllib.parse import urlparse


_ALLOWED_EXACT_HOSTS = {
    "steamcommunity.com",
    "steampowered.com",
}

_ALLOWED_HOST_SUFFIXES = (
    ".steamcommunity.com",
    ".steampowered.com",
)


def is_allowed_workshop_browser_url(raw_url: str | None) -> bool:
    raw_url = (raw_url or "").strip()
    if raw_url == "about:blank":
        return True

    parsed = urlparse(raw_url)
    if parsed.scheme.lower() not in {"http", "https"}:
        return False

    host = (parsed.hostname or "").lower().rstrip(".")
    return host in _ALLOWED_EXACT_HOSTS or host.endswith(_ALLOWED_HOST_SUFFIXES)
