from core.workshop_browser_policy import is_allowed_workshop_browser_url


def test_browser_policy_allows_steam_owned_pages():
    assert is_allowed_workshop_browser_url("about:blank")
    assert is_allowed_workshop_browser_url("https://steamcommunity.com/app/281990/workshop/")
    assert is_allowed_workshop_browser_url("https://store.steampowered.com/app/281990/")
    assert is_allowed_workshop_browser_url("https://help.steampowered.com/en/")


def test_browser_policy_rejects_lookalike_and_non_web_urls():
    assert not is_allowed_workshop_browser_url("https://steamcommunity.com.example.org/")
    assert not is_allowed_workshop_browser_url("https://evilsteampowered.com/")
    assert not is_allowed_workshop_browser_url("file:///C:/Windows/System32/")
    assert not is_allowed_workshop_browser_url("javascript:alert(1)")
