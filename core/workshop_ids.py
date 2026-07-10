import re
from urllib.parse import parse_qs, urlparse

from core.workshop_browser_config import WORKSHOP_DETAIL_PATH_PREFIXES


def extract_workshop_id(raw_text: str | None) -> str | None:
    raw_text = (raw_text or "").strip()
    if not raw_text:
        return None

    if raw_text.isdigit():
        return raw_text

    try:
        parsed = urlparse(raw_text)
        query = parse_qs(parsed.query)

        workshop_id = None
        if "id" in query and query["id"] and query["id"][0].isdigit():
            workshop_id = query["id"][0]

        if not workshop_id:
            path_parts = [part for part in parsed.path.split("/") if part]
            if path_parts and path_parts[-1].isdigit():
                workshop_id = path_parts[-1]

        if not workshop_id:
            match = re.search(r"(\d{6,20})", raw_text)
            if match:
                workshop_id = match.group(1)

        if workshop_id and workshop_id.isdigit():
            return workshop_id
    except Exception:
        return None

    return None


def extract_steam_workshop_page_id(raw_url: str | None) -> str | None:
    raw_url = (raw_url or "").strip()
    if not raw_url:
        return None

    parsed = urlparse(raw_url)
    host = (parsed.hostname or "").lower()
    path = parsed.path.lower()
    if host != "steamcommunity.com" and not host.endswith(".steamcommunity.com"):
        return None
    if not any(path.startswith(prefix) for prefix in WORKSHOP_DETAIL_PATH_PREFIXES):
        return None
    return extract_workshop_id(raw_url)
