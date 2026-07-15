from core.workshop_browser_config import get_workshop_dom_adapter_payload


def test_dom_adapters_are_declarative_and_named():
    adapters = get_workshop_dom_adapter_payload()

    assert [adapter["name"] for adapter in adapters] == ["steam-modern", "steam-legacy"]
    assert all(adapter["linkSelectors"] for adapter in adapters)
    assert all(adapter["cardSelectors"] for adapter in adapters)
    assert all(adapter["idAttributes"] for adapter in adapters)


def test_modern_adapter_supports_data_attributes_and_semantic_cards():
    modern = get_workshop_dom_adapter_payload()[0]

    assert "data-publishedfileid" in modern["idAttributes"]
    assert "article" in modern["cardSelectors"]
    assert '[role="listitem"]' in modern["cardSelectors"]
