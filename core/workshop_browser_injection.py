import json
from typing import Iterable

from core.workshop_browser_config import (
    WORKSHOP_DETAIL_PATH_PREFIXES,
    get_workshop_dom_adapter_payload,
)


_CONFIG_PLACEHOLDER = "__STELLARIS_WORKSHOP_CONFIG__"


def _json(value) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def build_queue_cleanup_script() -> str:
    return """
(function() {
    const integration = window.__stellarisWorkshopIntegration;
    if (integration && typeof integration.cleanup === 'function') {
        integration.cleanup();
    } else {
        document.querySelectorAll('.stellaris-queue-button').forEach((button) => button.remove());
    }
    if (window.__stellarisQueueObserver) {
        try { window.__stellarisQueueObserver.disconnect(); } catch (error) {}
        window.__stellarisQueueObserver = null;
    }
})();
"""


_QUEUE_SYNC_RUNTIME = r"""
(function() {
    const config = __STELLARIS_WORKSHOP_CONFIG__;
    const buttonClass = 'stellaris-queue-button';
    const queuedIds = new Set(config.queuedIds);
    const downloadedIds = new Set(config.downloadedIds);

    function isNumericId(value) {
        return typeof value === 'string' && /^\d+$/.test(value);
    }

    function extractIdFromUrl(url) {
        if (!url) return null;
        try {
            const parsed = new URL(url, window.location.origin);
            const queryId = parsed.searchParams.get('id');
            if (isNumericId(queryId)) return queryId;
            const pathParts = parsed.pathname.split('/').filter(Boolean);
            for (let index = pathParts.length - 1; index >= 0; index--) {
                if (isNumericId(pathParts[index])) return pathParts[index];
            }
        } catch (error) {}
        return null;
    }

    function extractIdFromAttributes(element, attributeNames) {
        if (!(element instanceof Element)) return null;
        for (const attributeName of attributeNames) {
            const value = element.getAttribute(attributeName);
            if (isNumericId(value)) return value;
        }
        return null;
    }

    function extractWorkshopId(link, adapter) {
        let node = link;
        for (let depth = 0; node && depth <= adapter.ancestorDepth; depth++) {
            const attributeId = extractIdFromAttributes(node, adapter.idAttributes);
            if (attributeId) return attributeId;
            node = node.parentElement;
        }
        return extractIdFromUrl(link.href);
    }

    function isDetailPage() {
        const path = window.location.pathname.toLowerCase();
        return config.detailPathPrefixes.some((prefix) => path.startsWith(prefix));
    }

    function isUsableCard(element) {
        if (!(element instanceof HTMLElement)) return false;
        if (element === document.body || element === document.documentElement) return false;
        const rect = element.getBoundingClientRect();
        if (rect.width < 80 || rect.height < 60) return false;
        if (rect.width > Math.max(window.innerWidth * 0.95, 1280)) return false;
        if (rect.height > Math.max(window.innerHeight * 0.85, 760)) return false;
        return true;
    }

    function matchesAnySelector(element, selectors) {
        return selectors.some((selector) => {
            try { return element.matches(selector); } catch (error) { return false; }
        });
    }

    function scoreCardCandidate(element, link, adapter) {
        if (!isUsableCard(element)) return -1;
        const rect = element.getBoundingClientRect();
        const className = String(element.className || '').toLowerCase();
        let score = 0;

        if (extractIdFromAttributes(element, adapter.idAttributes)) score += 40;
        if (matchesAnySelector(element, adapter.cardSelectors)) score += 30;
        for (const hint of adapter.classHints) {
            if (className.includes(hint)) score += 8;
        }
        if (element.querySelector('img, picture, [style*="background-image"]')) score += 18;
        if (element.querySelector('a[href*="sharedfiles/filedetails"], a[href*="/workshop/filedetails"]')) score += 10;
        if (rect.width <= 520) score += 8;
        if (rect.height <= 420) score += 8;
        if (element.contains(link)) score += 5;
        score -= Math.max(0, Math.floor((rect.width * rect.height) / 180000));
        return score;
    }

    function findCardRoot(link, adapter) {
        let best = null;
        let bestScore = -1;
        let node = link;
        for (let depth = 0; node && depth <= adapter.ancestorDepth; depth++) {
            const score = scoreCardCandidate(node, link, adapter);
            if (score > bestScore) {
                best = node;
                bestScore = score;
            }
            node = node.parentElement;
        }
        return bestScore >= adapter.minimumScore ? best : null;
    }

    function requestToggle(workshopId) {
        const bridge = window.stellarisBridge;
        if (bridge && typeof bridge.toggleQueueItem === 'function') {
            bridge.toggleQueueItem(workshopId);
            return;
        }
        console.info('__STELLARIS_QUEUE__' + workshopId);
    }

    function connectWebChannel() {
        if (window.stellarisBridge || !window.qt || !window.qt.webChannelTransport) return;

        const createChannel = function() {
            if (typeof QWebChannel !== 'function' || window.stellarisBridge) return;
            new QWebChannel(window.qt.webChannelTransport, function(channel) {
                window.stellarisBridge = channel.objects.stellarisBridge;
            });
        };

        if (typeof QWebChannel === 'function') {
            createChannel();
            return;
        }
        if (document.querySelector('script[data-stellaris-webchannel]')) return;

        const script = document.createElement('script');
        script.src = 'qrc:///qtwebchannel/qwebchannel.js';
        script.dataset.stellarisWebchannel = 'true';
        script.onload = createChannel;
        (document.head || document.documentElement).appendChild(script);
    }

    function desiredButtonState(workshopId) {
        if (downloadedIds.has(workshopId)) return 'downloaded';
        if (queuedIds.has(workshopId)) return 'queued';
        return 'available';
    }

    function applyButtonState(button, workshopId) {
        const state = desiredButtonState(workshopId);
        if (button.dataset.workshopId === workshopId && button.dataset.state === state) return;

        button.dataset.workshopId = workshopId;
        button.dataset.state = state;
        button.style.pointerEvents = 'auto';
        button.style.opacity = '0.94';

        if (state === 'downloaded') {
            button.textContent = '\u2713';
            button.title = config.tooltips.downloaded;
            button.setAttribute('aria-label', config.tooltips.downloaded);
            button.style.background = '#48b64a';
            button.style.cursor = 'default';
        } else if (state === 'queued') {
            button.textContent = '\u2212';
            button.title = config.tooltips.remove;
            button.setAttribute('aria-label', config.tooltips.remove);
            button.style.background = '#d98412';
            button.style.cursor = 'pointer';
        } else {
            button.textContent = '+';
            button.title = config.tooltips.add;
            button.setAttribute('aria-label', config.tooltips.add);
            button.style.background = '#2f8ef3';
            button.style.cursor = 'pointer';
        }
    }

    function applyOptimisticToggle(button) {
        const workshopId = button.dataset.workshopId;
        if (!workshopId || downloadedIds.has(workshopId)) return;
        if (queuedIds.has(workshopId)) queuedIds.delete(workshopId);
        else queuedIds.add(workshopId);
        applyButtonState(button, workshopId);
    }

    function createButton(card, workshopId) {
        let button = Array.from(card.children).find((child) =>
            child.classList && child.classList.contains(buttonClass)
        );
        if (!button) {
            if (getComputedStyle(card).position === 'static') card.style.position = 'relative';
            button = document.createElement('button');
            button.className = buttonClass;
            button.type = 'button';
            Object.assign(button.style, {
                position: 'absolute', top: '8px', right: '8px', width: '34px', height: '34px',
                border: '0', borderRadius: '6px', boxShadow: '0 6px 18px rgba(0,0,0,0.35)',
                color: '#ffffff', fontSize: '20px', fontWeight: '700', lineHeight: '1',
                zIndex: '2147483647', display: 'flex', alignItems: 'center',
                justifyContent: 'center', transition: 'transform 0.15s ease, opacity 0.15s ease'
            });
            button.onmouseenter = () => {
                button.style.transform = 'scale(1.06)';
                button.style.opacity = '1';
            };
            button.onmouseleave = () => {
                button.style.transform = 'scale(1)';
                button.style.opacity = '0.94';
            };
            button.addEventListener('click', function(event) {
                event.preventDefault();
                event.stopPropagation();
                if (event.stopImmediatePropagation) event.stopImmediatePropagation();
                if (downloadedIds.has(workshopId)) return;
                applyOptimisticToggle(button);
                requestToggle(workshopId);
            }, true);
            card.appendChild(button);
        }
        applyButtonState(button, workshopId);
    }

    function injectButtons() {
        if (isDetailPage()) {
            document.querySelectorAll('.' + buttonClass).forEach((button) => button.remove());
            return;
        }

        const seen = new Set();
        for (const adapter of config.adapters) {
            for (const selector of adapter.linkSelectors) {
                let links = [];
                try { links = document.querySelectorAll(selector); } catch (error) { continue; }
                links.forEach((link) => {
                    const workshopId = extractWorkshopId(link, adapter);
                    if (!workshopId || seen.has(workshopId)) return;
                    const card = findCardRoot(link, adapter);
                    if (!card) return;
                    seen.add(workshopId);
                    createButton(card, workshopId);
                });
            }
        }
    }

    let injectTimer = null;
    function scheduleInject() {
        if (injectTimer !== null) return;
        injectTimer = window.setTimeout(function() {
            injectTimer = null;
            injectButtons();
        }, 120);
    }

    const previous = window.__stellarisWorkshopIntegration;
    if (previous && typeof previous.cleanup === 'function') previous.cleanup();
    if (window.__stellarisQueueObserver) {
        try { window.__stellarisQueueObserver.disconnect(); } catch (error) {}
        window.__stellarisQueueObserver = null;
    }

    const observer = new MutationObserver(scheduleInject);
    if (document.body) observer.observe(document.body, {childList: true, subtree: true});

    const refreshTimers = [];
    window.__stellarisWorkshopIntegration = {
        observer: observer,
        inject: injectButtons,
        cleanup: function() {
            observer.disconnect();
            if (injectTimer !== null) window.clearTimeout(injectTimer);
            refreshTimers.forEach((timerId) => window.clearTimeout(timerId));
            document.querySelectorAll('.' + buttonClass).forEach((button) => button.remove());
        }
    };

    connectWebChannel();
    injectButtons();
    refreshTimers.push(window.setTimeout(injectButtons, 300));
    refreshTimers.push(window.setTimeout(injectButtons, 1000));
    refreshTimers.push(window.setTimeout(injectButtons, 2500));
})();
"""


def build_queue_sync_script(
    queued_ids: Iterable[str],
    downloaded_ids: Iterable[str],
    add_tooltip: str,
    remove_tooltip: str,
    downloaded_tooltip: str,
) -> str:
    config = {
        "queuedIds": [str(workshop_id) for workshop_id in queued_ids],
        "downloadedIds": [str(workshop_id) for workshop_id in downloaded_ids],
        "detailPathPrefixes": list(WORKSHOP_DETAIL_PATH_PREFIXES),
        "tooltips": {
            "add": add_tooltip,
            "remove": remove_tooltip,
            "downloaded": downloaded_tooltip,
        },
        "adapters": get_workshop_dom_adapter_payload(),
    }
    return _QUEUE_SYNC_RUNTIME.replace(_CONFIG_PLACEHOLDER, _json(config), 1)
