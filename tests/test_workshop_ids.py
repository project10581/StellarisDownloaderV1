from core.workshop_ids import extract_steam_workshop_page_id, extract_workshop_id


def test_extract_workshop_id_from_numeric_text():
    assert extract_workshop_id("281990123456") == "281990123456"


def test_extract_workshop_id_from_steam_url_query():
    assert (
        extract_workshop_id("https://steamcommunity.com/sharedfiles/filedetails/?id=123456789")
        == "123456789"
    )


def test_extract_steam_workshop_page_id_requires_steam_detail_page():
    assert (
        extract_steam_workshop_page_id("https://steamcommunity.com/sharedfiles/filedetails/?id=123456789")
        == "123456789"
    )
    assert extract_steam_workshop_page_id("https://example.com/sharedfiles/filedetails/?id=123456789") is None


def test_extract_steam_workshop_page_id_accepts_steam_host_with_port():
    assert (
        extract_steam_workshop_page_id(
            "https://steamcommunity.com:443/sharedfiles/filedetails/?id=123456789"
        )
        == "123456789"
    )
