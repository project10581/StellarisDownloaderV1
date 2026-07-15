# Workshop Browser Integration

The embedded browser is divided into stable infrastructure and replaceable Steam adapters.

## Module boundaries

- `workshop_browser_dialog.py`
  - Builds the dialog, navigation toolbar, queue panel, and download handoff.
  - Caches downloaded Workshop IDs for the lifetime of the dialog.
  - Does not contain navigation policy, popup handling, DOM selectors, or injected JavaScript.
- `ui/workshop_web.py`
  - Owns Qt WebEngine classes, popup forwarding, the WebChannel object, and the console fallback bridge.
  - Should not know how Steam item cards are structured.
- `core/workshop_browser_policy.py`
  - Owns the Steam-owned URL allow-list.
  - Has no Qt dependency and is covered by pure logic tests.
- `core/workshop_browser_config.py`
  - Owns Workshop detail-route prefixes and DOM adapter declarations.
  - This is the first file to edit after a Steam Workshop UI change.
- `core/workshop_browser_injection.py`
  - Owns the generic JavaScript runtime.
  - Consumes adapter data, locates cards, renders queue buttons, observes dynamic content, and connects to Qt WebChannel.
- `core/workshop_ids.py`
  - Extracts Workshop IDs from raw IDs and supported Steam detail URLs.
- `core/workshop_queue.py`
  - Maintains an ordered, duplicate-free queue independently of Qt widgets.

## Adapter contract

Each `WorkshopDomAdapter` declares:

- `link_selectors`: selectors that find links associated with Workshop items.
- `card_selectors`: semantic or Steam-specific selectors that identify likely card roots.
- `id_attributes`: data attributes that may contain a published-file ID.
- `class_hints`: low-weight words used when scoring an ancestor as a card.
- `ancestor_depth`: maximum number of ancestors inspected from a matching link.
- `minimum_score`: confidence threshold before a button is attached.

The generic `steam-modern` adapter runs first. The narrower `steam-legacy` adapter remains as a fallback. A new Steam layout should normally be supported by adding another adapter before changing the injection engine.

## Bridge behavior

The injected script first tries the registered Qt WebChannel object:

```text
stellarisBridge.toggleQueueItem(workshopId)
```

If WebChannel initialization is delayed or blocked, it falls back to a console message:

```text
__STELLARIS_QUEUE__<workshopId>
```

`RestrictedWorkshopPage` handles both transports. Keep the fallback while Qt WebEngine versions differ between packaged releases.

## Steam UI migration checklist

1. Inspect one listing page and one detail page in the embedded browser.
2. Confirm item links still expose either an `id` query parameter, a numeric path segment, or an ID data attribute.
3. Add or update a `WorkshopDomAdapter` in `core/workshop_browser_config.py`.
4. Extend adapter and script-generation tests without importing Qt.
5. Change `core/workshop_browser_injection.py` only if Steam changed behavior that cannot be expressed by adapter data.
6. Verify infinite scrolling, queue add/remove, downloaded-state buttons, detail-page cleanup, popup forwarding, back/forward, and reload.

The runtime avoids rewriting unchanged button state so Steam's mutation observer and the application's observer do not continuously trigger each other.
