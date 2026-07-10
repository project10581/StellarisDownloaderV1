from dataclasses import dataclass


WORKSHOP_DETAIL_PATH_PREFIXES = (
    "/sharedfiles/filedetails",
    "/workshop/filedetails",
)


@dataclass(frozen=True)
class WorkshopDomAdapter:
    """Declarative description of a Steam Workshop result-card layout."""

    name: str
    link_selectors: tuple[str, ...]
    card_selectors: tuple[str, ...]
    id_attributes: tuple[str, ...]
    class_hints: tuple[str, ...]
    ancestor_depth: int = 10
    minimum_score: int = 10

    def to_payload(self) -> dict:
        return {
            "name": self.name,
            "linkSelectors": list(self.link_selectors),
            "cardSelectors": list(self.card_selectors),
            "idAttributes": list(self.id_attributes),
            "classHints": list(self.class_hints),
            "ancestorDepth": self.ancestor_depth,
            "minimumScore": self.minimum_score,
        }


STEAM_WORKSHOP_DOM_ADAPTERS = (
    WorkshopDomAdapter(
        name="steam-modern",
        link_selectors=(
            'a[href*="/sharedfiles/filedetails"]',
            'a[href*="/workshop/filedetails"]',
        ),
        card_selectors=(
            "[data-publishedfileid]",
            "[data-published-file-id]",
            "[data-workshop-id]",
            "[data-itemid]",
            "article",
            '[role="listitem"]',
        ),
        id_attributes=(
            "data-publishedfileid",
            "data-published-file-id",
            "data-workshop-id",
            "data-itemid",
        ),
        class_hints=(
            "workshop",
            "publishedfile",
            "browseitem",
            "collectionitem",
            "item",
            "card",
            "tile",
        ),
    ),
    WorkshopDomAdapter(
        name="steam-legacy",
        link_selectors=(
            "a.workshopItemTitle",
            ".workshopItem a[href]",
            ".workshopBrowseItem a[href]",
        ),
        card_selectors=(
            ".workshopItem",
            ".workshopBrowseItem",
            ".workshopItemPreviewHolder",
        ),
        id_attributes=("data-publishedfileid", "data-itemid"),
        class_hints=("workshopitem", "workshopbrowseitem", "item"),
        ancestor_depth=8,
        minimum_score=8,
    ),
)


def get_workshop_dom_adapter_payload() -> list[dict]:
    return [adapter.to_payload() for adapter in STEAM_WORKSHOP_DOM_ADAPTERS]
