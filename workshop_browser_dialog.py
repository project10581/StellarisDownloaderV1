from PySide6.QtCore import QUrl, Qt
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from core.database import ModDatabase
from core.i18n import tr
from core.workshop_browser_injection import build_queue_cleanup_script, build_queue_sync_script
from core.workshop_ids import extract_steam_workshop_page_id
from core.workshop_queue import WorkshopQueue
from ui.workshop_web import RestrictedWorkshopPage, WorkshopBrowserView, WorkshopQueueBridge
from workshop_title_lookup import WorkshopTitleLookupThread


class WorkshopBrowserDialog(QDialog):
    """Embedded browser shell for browsing the Stellaris Workshop."""

    WORKSHOP_URL = "https://steamcommunity.com/app/281990/workshop/"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.queue = WorkshopQueue()
        self.downloaded_workshop_ids = set()
        self.title_lookup_threads = {}
        self.current_workshop_id = None
        self.queue_bridge = WorkshopQueueBridge()
        self.queue_bridge.queue_toggled.connect(self.toggle_queue_item_from_js)

        self.setWindowTitle(tr("dialog_workshop_browser"))
        self.resize(1400, 850)
        self.setModal(True)

        main_layout = QVBoxLayout(self)

        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter, 1)

        queue_panel = QWidget()
        queue_layout = QVBoxLayout(queue_panel)
        queue_layout.setContentsMargins(8, 8, 8, 8)
        queue_layout.setSpacing(8)

        self.queue_label = QLabel(f"{tr('label_selected_mods')} (0)")
        queue_layout.addWidget(self.queue_label)

        self.queue_list = QListWidget()
        self.queue_list.setSelectionMode(QListWidget.MultiSelection)
        self.queue_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.queue_list.customContextMenuRequested.connect(self.show_queue_context_menu)
        queue_layout.addWidget(self.queue_list, 1)

        self.queue_add_button = QPushButton(tr("button_add_to_list"))
        self.queue_add_button.clicked.connect(self.add_current_mod)
        queue_layout.addWidget(self.queue_add_button)

        self.download_queue_button = QPushButton(tr("button_download_queue"))
        self.download_queue_button.clicked.connect(self.download_queue)
        queue_layout.addWidget(self.download_queue_button)

        self.remove_selected_button = QPushButton(tr("button_remove_selected"))
        self.remove_selected_button.clicked.connect(self.remove_selected)
        queue_layout.addWidget(self.remove_selected_button)

        self.clear_list_button = QPushButton(tr("button_clear_list"))
        self.clear_list_button.clicked.connect(self.clear_list)
        queue_layout.addWidget(self.clear_list_button)

        splitter.addWidget(queue_panel)

        browser_panel = QWidget()
        browser_layout = QVBoxLayout(browser_panel)
        browser_layout.setContentsMargins(8, 8, 8, 8)
        browser_layout.setSpacing(8)

        self.page_title_label = QLabel(tr("label_current_page"))
        self.page_title_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        browser_layout.addWidget(self.page_title_label)

        self.url_edit = QLineEdit()
        self.url_edit.setReadOnly(True)
        self.url_edit.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        self.url_edit.setMinimumWidth(0)
        browser_layout.addWidget(self.url_edit)

        nav_layout = QHBoxLayout()
        self.back_button = QPushButton(tr("button_back"))
        self.back_button.clicked.connect(self.go_back)
        nav_layout.addWidget(self.back_button)

        self.forward_button = QPushButton(tr("button_forward"))
        self.forward_button.clicked.connect(self.go_forward)
        nav_layout.addWidget(self.forward_button)

        self.reload_button = QPushButton(tr("button_reload"))
        self.reload_button.clicked.connect(self.reload_page)
        nav_layout.addWidget(self.reload_button)

        self.add_current_button = QPushButton(tr("button_add_current_mod"))
        self.add_current_button.clicked.connect(self.add_current_mod)
        self.add_current_button.setVisible(False)
        nav_layout.addWidget(self.add_current_button)

        nav_layout.addStretch()
        browser_layout.addLayout(nav_layout)

        self.browser_view = WorkshopBrowserView()
        self.browser_page = RestrictedWorkshopPage(
            self.show_blocked_page,
            self.toggle_queue_item_from_js,
            self.browser_view,
        )
        self.web_channel = QWebChannel(self.browser_page)
        self.web_channel.registerObject("stellarisBridge", self.queue_bridge)
        self.browser_page.setWebChannel(self.web_channel)
        self.browser_view.setPage(self.browser_page)
        self.browser_view.urlChanged.connect(self.on_browser_url_changed)
        self.browser_view.titleChanged.connect(self.on_browser_title_changed)
        self.browser_view.loadFinished.connect(self.on_browser_load_finished)
        browser_layout.addWidget(self.browser_view, 1)

        splitter.addWidget(browser_panel)

        splitter.setSizes([360, 1040])

        self.refresh_downloaded_workshop_ids()
        self.update_current_mod_state()
        self.browser_view.setUrl(QUrl(self.WORKSHOP_URL))

    @staticmethod
    def extract_mod_page_workshop_id(url):
        if isinstance(url, QUrl):
            url = url.toString()
        return extract_steam_workshop_page_id(url)

    def show_blocked_page(self):
        self.browser_view.setHtml("")
        self.url_edit.clear()
        self.page_title_label.setText(tr("label_current_page"))
        self.current_workshop_id = None
        self.update_current_mod_state()

    def update_current_mod_state(self):
        has_mod = bool(self.current_workshop_id)
        self.add_current_button.setVisible(has_mod)
        self.queue_add_button.setEnabled(has_mod)

    def refresh_downloaded_workshop_ids(self):
        if not self.parent_window:
            self.downloaded_workshop_ids = set()
            return
        db = ModDatabase(self.parent_window.db_path)
        self.downloaded_workshop_ids = {
            mod["workshop_id"]
            for mod in db.list_all_mods()
            if mod.get("status") == "success"
        }

    def get_queue_sync_script(self):
        return build_queue_sync_script(
            queued_ids=self.queue.ids,
            downloaded_ids=self.downloaded_workshop_ids,
            add_tooltip=tr("tooltip_add_to_queue"),
            remove_tooltip=tr("tooltip_remove_from_queue"),
            downloaded_tooltip=tr("tooltip_already_downloaded"),
        )

    def sync_browser_queue_state(self):
        if not self.browser_view:
            return
        current_url = self.browser_view.url()
        if self.extract_mod_page_workshop_id(current_url):
            self.browser_view.page().runJavaScript(build_queue_cleanup_script())
            return
        self.browser_view.page().runJavaScript(self.get_queue_sync_script())

    def on_browser_load_finished(self, _ok):
        self.sync_browser_queue_state()

    def update_queue_ui(self):
        self.queue_list.clear()
        for wid in self.queue.ids:
            item = QListWidgetItem(
                tr("label_queue_item").format(
                    title=self.queue.title_for(wid, tr("unknown_mod")),
                    workshop_id=wid,
                )
            )
            item.setData(Qt.UserRole, wid)
            self.queue_list.addItem(item)
        self.queue_label.setText(f"{tr('label_selected_mods')} ({len(self.queue)})")
        self.sync_browser_queue_state()

    def ensure_queue_title_async(self, workshop_id):
        if self.queue.title_for(workshop_id, tr("unknown_mod")) != tr("unknown_mod"):
            return
        if workshop_id in self.title_lookup_threads:
            return

        db_path = self.parent_window.db_path if self.parent_window else None
        worker = WorkshopTitleLookupThread(workshop_id, db_path)
        worker.resolved.connect(self.on_queue_title_resolved)
        worker.finished.connect(lambda wid=workshop_id: self.title_lookup_threads.pop(wid, None))
        self.title_lookup_threads[workshop_id] = worker
        worker.start()

    def on_queue_title_resolved(self, workshop_id, title):
        self.queue.set_title(workshop_id, title or tr("unknown_mod"))
        if workshop_id in self.queue:
            self.update_queue_ui()

    def on_browser_url_changed(self, url):
        self.url_edit.setText(url.toString())
        self.current_workshop_id = self.extract_mod_page_workshop_id(url)
        self.update_current_mod_state()

    def on_browser_title_changed(self, title):
        self.page_title_label.setText(f"{tr('label_current_page')}: {title or self.WORKSHOP_URL}")

    def go_back(self):
        self.browser_view.back()

    def go_forward(self):
        self.browser_view.forward()

    def reload_page(self):
        self.browser_view.reload()

    def add_current_mod(self):
        if not self.current_workshop_id:
            QMessageBox.warning(
                self,
                tr("warning_invalid_workshop_page_title"),
                tr("warning_invalid_workshop_page_message"),
            )
            return

        if self.current_workshop_id in self.queue:
            QMessageBox.information(
                self,
                tr("info_duplicate_title"),
                tr("info_duplicate_message").format(workshop_id=self.current_workshop_id),
            )
            return

        self.queue.add(self.current_workshop_id, tr("unknown_mod"))
        self.update_queue_ui()
        self.ensure_queue_title_async(self.current_workshop_id)

    def toggle_queue_item_from_js(self, workshop_id):
        added = self.queue.toggle(workshop_id, tr("unknown_mod"))
        if not added:
            self.update_queue_ui()
            return

        self.update_queue_ui()
        self.ensure_queue_title_async(workshop_id)

    def remove_selected(self):
        for item in self.queue_list.selectedItems():
            wid = item.data(Qt.UserRole)
            self.queue.remove(wid)
        self.update_queue_ui()

    def clear_list(self):
        self.queue.clear()
        self.update_queue_ui()

    def show_queue_context_menu(self, position):
        item = self.queue_list.itemAt(position)
        if not item:
            return

        selected_items = self.queue_list.selectedItems()
        selected_ids = [selected_item.data(Qt.UserRole) for selected_item in selected_items]
        wid = item.data(Qt.UserRole)
        remove_ids = [wid]
        remove_label = tr("button_remove_this_mod")
        if len(selected_ids) > 1 and wid in selected_ids:
            remove_ids = selected_ids
            remove_label = tr("button_remove_selected_mods")

        menu = QMenu(self)
        remove_action = menu.addAction(remove_label)
        chosen_action = menu.exec(self.queue_list.mapToGlobal(position))
        if chosen_action == remove_action:
            self.queue.remove_many(remove_ids)
            self.update_queue_ui()

    def download_queue(self):
        if not self.queue:
            QMessageBox.information(self, tr("info_no_mods_title"), tr("info_browser_queue_empty"))
            return
        started = self.parent_window.start_download_for_ids(list(self.queue.ids))
        if not started:
            return
        self.queue.clear()
        self.update_queue_ui()
        self.accept()
