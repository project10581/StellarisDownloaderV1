from PySide6.QtCore import QObject, QTimer, QUrl, QUrlQuery, Signal, Slot
from PySide6.QtWebEngineCore import QWebEnginePage
from PySide6.QtWebEngineWidgets import QWebEngineView

from core.workshop_browser_policy import is_allowed_workshop_browser_url


class WorkshopQueueBridge(QObject):
    queue_toggled = Signal(str)

    @Slot(str)
    def toggleQueueItem(self, workshop_id):
        self.queue_toggled.emit(workshop_id)


class RestrictedWorkshopPage(QWebEnginePage):
    """Restrict navigation and relay queue requests from injected JavaScript."""

    QUEUE_CONSOLE_PREFIX = "__STELLARIS_QUEUE__"

    def __init__(self, block_callback=None, queue_toggle_callback=None, parent=None):
        super().__init__(parent)
        self.block_callback = block_callback
        self.queue_toggle_callback = queue_toggle_callback
        self.host_view = parent if isinstance(parent, QWebEngineView) else None

    @staticmethod
    def is_allowed_url(url):
        return bool(url and url.isValid() and is_allowed_workshop_browser_url(url.toString()))

    def _queue_toggle(self, workshop_id):
        if workshop_id and self.queue_toggle_callback:
            QTimer.singleShot(0, lambda wid=workshop_id: self.queue_toggle_callback(wid))

    def acceptNavigationRequest(self, url, nav_type, is_main_frame):
        if url.scheme() == "stellarisqueue":
            self._queue_toggle(QUrlQuery(url).queryItemValue("id"))
            return False

        if self.is_allowed_url(url):
            return True
        if is_main_frame and self.block_callback:
            QTimer.singleShot(0, self.block_callback)
        return False

    def createWindow(self, _window_type):
        return _ForwardingWorkshopPage(self, self.host_view, self.host_view or self)

    def javaScriptConsoleMessage(self, level, message, line_number, source_id):
        if message.startswith(self.QUEUE_CONSOLE_PREFIX):
            self._queue_toggle(message[len(self.QUEUE_CONSOLE_PREFIX):].strip())
            return
        super().javaScriptConsoleMessage(level, message, line_number, source_id)


class _ForwardingWorkshopPage(QWebEnginePage):
    """Route popup navigations back into the main Workshop page."""

    def __init__(self, target_page, target_view=None, parent=None):
        super().__init__(target_page.profile(), parent or target_page)
        self.target_page = target_page
        self.target_view = target_view

    def _forward_url(self, url):
        if not url or not url.isValid() or url.toString() == "about:blank":
            return

        if self.target_page.is_allowed_url(url):
            if self.target_view:
                QTimer.singleShot(0, lambda target=QUrl(url): self.target_view.setUrl(target))
            else:
                QTimer.singleShot(0, lambda target=QUrl(url): self.target_page.load(target))
        elif self.target_page.block_callback:
            QTimer.singleShot(0, self.target_page.block_callback)

        QTimer.singleShot(0, self.deleteLater)

    def acceptNavigationRequest(self, url, nav_type, is_main_frame):
        if url.toString() == "about:blank":
            return True
        self._forward_url(url)
        return False


class WorkshopBrowserView(QWebEngineView):
    """Embedded browser view that keeps popup links in the same view."""

    def createWindow(self, _window_type):
        current_page = self.page()
        if isinstance(current_page, RestrictedWorkshopPage):
            popup_view = QWebEngineView(self)
            popup_view.hide()
            popup_page = _ForwardingWorkshopPage(current_page, self, popup_view)
            popup_page.destroyed.connect(popup_view.deleteLater)
            popup_view.setPage(popup_page)
            return popup_view
        return super().createWindow(_window_type)
