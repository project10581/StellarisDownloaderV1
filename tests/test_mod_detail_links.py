from PySide6.QtCore import QUrl

from ui.mod_detail_panel import is_safe_external_link


def test_external_link_policy_allows_http_and_https():
    assert is_safe_external_link("https://steamcommunity.com/sharedfiles/filedetails/?id=123")
    assert is_safe_external_link(QUrl("http://example.com/mod-info"))


def test_external_link_policy_rejects_local_and_custom_protocols():
    assert not is_safe_external_link("file:///C:/Windows/System32/")
    assert not is_safe_external_link("steam://run/281990")
    assert not is_safe_external_link("javascript:alert(1)")
    assert not is_safe_external_link("/relative/path")
