import logging
import sys
import os
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QLabel, QLineEdit, QComboBox,
    QSplitter,
    QDialog, QMenu, QMessageBox
)
from PySide6.QtCore import Qt, QUrl, QTimer
from PySide6.QtGui import QDesktopServices, QAction

from core.database import ModDatabase
from core.i18n import tr
from core.library_root import validate_library_root
from core.mod_service import delete_mod_files_and_record
from core.runtime_paths import configure_logging, get_db_path, get_settings_path
from core.settings import SettingsManager
from core.version import __version__
from ui.app_update_flow import run_app_update_check as run_app_update_check_flow
from ui.app_update_flow import start_app_update_download as start_app_update_download_flow
from ui.download_flow import start_download_sequence
from ui.library_reload import append_library_reload_change_log, show_library_reload_changes_dialog
from ui.mod_list import ModListItem, mod_matches_search, sort_mod_records
from ui.mod_detail_panel import ModDetailPanel
from ui.mod_update_flow import run_mod_update_check as run_mod_update_check_flow
from ui.mod_update_flow import run_update_all
from ui.progress import OperationProgressDialog, update_operation_progress
from ui.workers import StartupLibraryRefreshThread, retain_worker
from settings_dialog import SettingsDialog
from download_dialog import DownloadFromUrlIdDialog
from workshop_browser_dialog import WorkshopBrowserDialog


class MainWindow(QMainWindow):
    """Main application window."""
    
    def __init__(self):
        super().__init__()
        self.db_path = get_db_path()
        self.settings_path = get_settings_path()
        # Keep references to worker threads to prevent garbage collection
        self.worker_threads = []
        self.init_ui()
        self.refresh_mod_list()
        QTimer.singleShot(0, self.refresh_mod_db_on_startup_if_enabled)
        QTimer.singleShot(0, self.run_startup_checks_if_enabled)
    
    def init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle(f"{tr('app_title')} v{__version__}")
        self.setGeometry(100, 100, 1400, 800)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Top bar with menus
        self.create_menu_bar()
        
        # Two-pane layout
        splitter = QSplitter(Qt.Horizontal)
        splitter.setContentsMargins(0, 0, 0, 0)
        
        # Left pane: Mod detail panel (narrower)
        self.detail_panel = ModDetailPanel()
        splitter.addWidget(self.detail_panel)
        
        # Right pane: Mod list with search/sort controls  
        list_container = QWidget()
        list_layout = QVBoxLayout(list_container)
        list_layout.setContentsMargins(5, 5, 5, 5)
        list_layout.setSpacing(5)
        
        # Search and sort controls - NOW IN RIGHT PANE ONLY
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(5)
        
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText(tr("placeholder_search_mods"))
        self.search_edit.textChanged.connect(self.filter_mods)
        controls_layout.addWidget(QLabel(tr("label_search")))
        controls_layout.addWidget(self.search_edit)

        controls_layout.addWidget(QLabel(tr("label_sort")))
        self.sort_combo = QComboBox()
        self.sort_combo.addItem(tr("sort_alphabetical"), "alphabetical")
        self.sort_combo.addItem(tr("sort_last_workshop_update"), "last_workshop_update")
        self.sort_combo.addItem(tr("sort_last_download_time"), "last_download_time")
        self.sort_combo.addItem(tr("sort_file_size"), "file_size")
        self.sort_combo.currentIndexChanged.connect(lambda _index: self.sort_mods())
        controls_layout.addWidget(self.sort_combo)
        
        list_layout.addLayout(controls_layout)
        
        # Mod list
        self.mod_list = QListWidget()
        self.mod_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.mod_list.customContextMenuRequested.connect(self.show_mod_list_context_menu)
        self.mod_list.itemClicked.connect(self.on_mod_selected)
        list_layout.addWidget(self.mod_list)
        
        splitter.addWidget(list_container)
        
        # Set initial splitter proportions (detail panel wider now)
        splitter.setSizes([500, 900])
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        
        main_layout.addWidget(splitter)
        
        central_widget.setLayout(main_layout)
    
    def create_menu_bar(self):
        """Create the menu bar."""
        menubar = self.menuBar()
        
        # Workshop menu
        workshop_menu = menubar.addMenu(tr('menu_workshop'))
        
        download_action = QAction(tr('menu_download_from_url_id'), self)
        download_action.triggered.connect(self.show_download_from_url_or_id)
        workshop_menu.addAction(download_action)

        browse_workshop_action = QAction(tr('menu_browse_workshop'), self)
        browse_workshop_action.triggered.connect(self.show_workshop_browser)
        workshop_menu.addAction(browse_workshop_action)
        
        check_updates_action = QAction(tr('menu_check_updates'), self)
        check_updates_action.triggered.connect(self.show_check_updates)
        workshop_menu.addAction(check_updates_action)

        # Settings menu
        settings_menu = menubar.addMenu(tr('menu_settings'))
        
        settings_action = QAction(tr('menu_settings'), self)
        settings_action.triggered.connect(self.show_settings)
        settings_menu.addAction(settings_action)

        check_app_updates_action = QAction(tr('menu_check_app_updates'), self)
        check_app_updates_action.triggered.connect(self.show_app_update_check)
        settings_menu.addAction(check_app_updates_action)
    
    def show_download_from_url_or_id(self):
        """Show the unified download dialog for URL/ID."""
        dialog = DownloadFromUrlIdDialog(self)
        dialog.exec()
        self.refresh_mod_list()

    def show_workshop_browser(self):
        dialog = WorkshopBrowserDialog(self)
        dialog.exec()
        self.refresh_mod_list()

    def require_valid_library_root(self):
        settings = SettingsManager(self.settings_path)
        library_root = settings.get_library_root()
        is_valid, detail = validate_library_root(library_root)
        if is_valid:
            return library_root

        message_box = QMessageBox(self)
        message_box.setIcon(QMessageBox.Warning)
        message_box.setWindowTitle(tr("dialog_library_root_required"))
        message_box.setText(tr("warning_library_root_required_message"))
        if detail:
            message_box.setInformativeText(detail)
        open_settings_button = message_box.addButton(tr("button_open_settings"), QMessageBox.AcceptRole)
        message_box.addButton(tr("button_cancel"), QMessageBox.RejectRole)
        message_box.exec()

        if message_box.clickedButton() == open_settings_button:
            if self.show_settings():
                settings = SettingsManager(self.settings_path)
                library_root = settings.get_library_root()
                is_valid, detail = validate_library_root(library_root)
                if is_valid:
                    return library_root

        return None

    def start_download_for_ids(self, workshop_ids, finished_callback=None):
        download_root = self.require_valid_library_root()
        if not download_root:
            return False

        return start_download_sequence(
            self,
            self.db_path,
            self.worker_threads,
            download_root,
            workshop_ids,
            self.refresh_mod_list,
            finished_callback=finished_callback,
        )

    def show_check_updates(self):
        """Show check updates flow"""
        self.run_mod_update_check(silent=False)

    def run_mod_update_check(self, silent=False):
        run_mod_update_check_flow(
            self,
            self.db_path,
            self.worker_threads,
            self.refresh_mod_list,
            silent=silent,
        )

    def show_update_all(self):
        """Run update-all flow: check and apply updates for outdated mods."""
        download_root = self.require_valid_library_root()
        if not download_root:
            return

        run_update_all(self, self.db_path, download_root, self.worker_threads, self.refresh_mod_list)

    def show_settings(self):
        """Show settings dialog."""
        dialog = SettingsDialog(self)
        dialog.exec()
        if dialog.result() == QDialog.Accepted:
            self.refresh_mod_list()
            return True
        return False

    def show_app_update_check(self):
        self.run_app_update_check(silent=False)

    def run_app_update_check(self, silent=False):
        run_app_update_check_flow(self, self.worker_threads, silent=silent)

    def start_app_update_download(self, release):
        start_app_update_download_flow(self, self.worker_threads, release)

    def refresh_mod_db_on_startup_if_enabled(self):
        settings = SettingsManager(self.settings_path)
        if not settings.get_refresh_mod_db_on_startup():
            return

        library_root = settings.get_library_root()
        is_valid, detail = validate_library_root(library_root)
        if not is_valid or not library_root:
            if detail:
                logging.info(f"Skipping startup mod database refresh: {detail}")
            return

        self.mod_list.clear()
        self.all_mods = []
        self.detail_panel.clear_details()
        self.start_library_reload(
            library_root,
            title=tr("dialog_loading_library"),
            finished_callback=lambda _result: self.run_startup_checks_if_enabled(),
            error_callback=lambda _error: self.run_startup_checks_if_enabled(),
        )

    def run_startup_checks_if_enabled(self):
        settings = SettingsManager(self.settings_path)
        if settings.get_refresh_mod_db_on_startup():
            # If a refresh worker is currently running, let its completion callback trigger checks.
            active_refresh = any(isinstance(worker, StartupLibraryRefreshThread) and worker.isRunning() for worker in self.worker_threads)
            if active_refresh:
                return

        if settings.get_check_mod_updates_on_startup():
            QTimer.singleShot(0, lambda: self.run_mod_update_check(silent=False))
        if settings.get_check_app_updates_on_startup():
            QTimer.singleShot(0, lambda: self.run_app_update_check(silent=True))
    
    def refresh_mod_list(self):
        """Refresh the mod list from database."""
        # Store current search and sort settings
        current_search = self.search_edit.text()
        current_sort = self.sort_combo.currentData()
        
        self.mod_list.clear()
        db = ModDatabase(self.db_path)
        self.all_mods = db.list_all_mods()
        
        for mod in self.all_mods:
            item = ModListItem(mod)
            self.mod_list.addItem(item)
        
        # Restore search and sort
        self.search_edit.setText(current_search)
        index = self.sort_combo.findData(current_sort)
        if index >= 0:
            self.sort_combo.setCurrentIndex(index)
        self.filter_mods()
        self.sort_mods()

    def filter_mods(self):
        """Filter mods based on search text."""
        search_text = self.search_edit.text()
        
        for i in range(self.mod_list.count()):
            item = self.mod_list.item(i)
            item.setHidden(not mod_matches_search(item.mod_data, search_text))
    
    def sort_mods(self):
        """Sort mods based on selected criteria."""
        if not hasattr(self, 'all_mods'):
            return
            
        sort_by = self.sort_combo.currentData()
        self.all_mods = sort_mod_records(self.all_mods, sort_by)
        
        # Rebuild the list widget
        self.mod_list.clear()
        for mod in self.all_mods:
            item = ModListItem(mod)
            self.mod_list.addItem(item)
        
        # Reapply filter
        self.filter_mods()

    def get_mod_item_at_position(self, position):
        item = self.mod_list.itemAt(position)
        if item:
            self.mod_list.setCurrentItem(item)
            if not item.isSelected():
                self.mod_list.clearSelection()
                item.setSelected(True)
        return item

    def show_mod_list_context_menu(self, position):
        item = self.get_mod_item_at_position(position)
        if not item:
            return

        mod_data = item.mod_data
        menu = QMenu(self)

        refresh_action = menu.addAction(tr("button_refresh_list"))
        reload_library_action = menu.addAction(tr("button_reload_library"))
        menu.addSeparator()
        open_folder_action = menu.addAction(tr("button_open_mod_folder"))
        open_workshop_action = menu.addAction(tr("button_open_workshop_page"))
        menu.addSeparator()
        delete_action = menu.addAction(tr("button_delete_mod"))
        redownload_action = menu.addAction(tr("button_delete_mod_redownload"))

        chosen_action = menu.exec(self.mod_list.mapToGlobal(position))
        if chosen_action == refresh_action:
            self.refresh_mod_list()
        elif chosen_action == reload_library_action:
            self.reload_library_from_disk()
        elif chosen_action == open_folder_action:
            self.open_mod_folder_for_mod(mod_data)
        elif chosen_action == open_workshop_action:
            self.open_workshop_page_for_mod(mod_data)
        elif chosen_action == delete_action:
            self.delete_mod_from_disk_and_db(mod_data)
        elif chosen_action == redownload_action:
            self.delete_mod_and_redownload(mod_data)

    def open_mod_folder_for_mod(self, mod_data):
        content_path = (mod_data or {}).get("content_path")
        if content_path and os.path.exists(content_path):
            QDesktopServices.openUrl(QUrl.fromLocalFile(content_path))
            return
        QMessageBox.warning(self, tr("error_title"), tr("warning_mod_folder_not_found"))

    def open_workshop_page_for_mod(self, mod_data):
        workshop_id = (mod_data or {}).get("workshop_id")
        if not workshop_id:
            QMessageBox.warning(self, tr("error_title"), tr("warning_workshop_link_not_found"))
            return
        url = QUrl(f"https://steamcommunity.com/sharedfiles/filedetails/?id={workshop_id}")
        QDesktopServices.openUrl(url)

    def delete_mod_from_disk_and_db(self, mod_data, skip_confirmation=False):
        workshop_id = (mod_data or {}).get("workshop_id")
        if not workshop_id:
            return False

        title = mod_data.get("title") or tr("unknown_mod")
        if not skip_confirmation:
            answer = QMessageBox.question(
                self,
                tr("dialog_delete_mod"),
                tr("question_delete_mod_message").format(title=title, workshop_id=workshop_id),
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if answer != QMessageBox.Yes:
                return False

        try:
            library_root = SettingsManager(self.settings_path).get_library_root()
            delete_mod_files_and_record(self.db_path, library_root, mod_data)
            self.refresh_mod_list()
            self.detail_panel.clear_details()
            return True
        except Exception as exc:
            QMessageBox.critical(
                self,
                tr("error_title"),
                tr("error_delete_mod_message").format(error=exc),
            )
            return False

    def delete_mod_and_redownload(self, mod_data):
        workshop_id = (mod_data or {}).get("workshop_id")
        if not workshop_id:
            return

        download_root = self.require_valid_library_root()
        if not download_root:
            return

        title = mod_data.get("title") or tr("unknown_mod")
        answer = QMessageBox.question(
            self,
            tr("dialog_delete_mod_redownload"),
            tr("question_delete_mod_redownload_message").format(title=title, workshop_id=workshop_id),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return

        if not self.delete_mod_from_disk_and_db(mod_data, skip_confirmation=True):
            return

        self.start_download_for_ids([workshop_id])

    def start_library_reload(self, library_root, title=None, finished_callback=None, error_callback=None):
        self.mod_list.clear()
        self.all_mods = []
        self.detail_panel.clear_details()

        progress_dialog = OperationProgressDialog(title or tr("dialog_loading_library"), self)
        progress_dialog.set_overall(0, 0)
        progress_dialog.set_current(tr("status_scanning_library_root"))
        progress_dialog.show()

        worker = StartupLibraryRefreshThread(self.db_path, library_root)
        worker.progress.connect(
            lambda done, total, current: update_operation_progress(progress_dialog, done, total, current)
        )
        worker.log.connect(progress_dialog.append_log)

        def on_finished(result):
            append_library_reload_change_log(progress_dialog, result)
            progress_dialog.mark_done()
            self.refresh_mod_list()
            progress_dialog.close()
            show_library_reload_changes_dialog(result, self)
            if finished_callback:
                finished_callback(result)

        def on_error(error_message):
            logging.error("Library reload failed: %s", error_message)
            progress_dialog.close()
            QMessageBox.warning(
                self,
                tr("error_title"),
                tr("error_startup_refresh_mod_db_message").format(error=error_message),
            )
            if error_callback:
                error_callback(error_message)

        worker.result_ready.connect(on_finished)
        worker.error.connect(on_error)
        retain_worker(self.worker_threads, worker)
        worker.start()

    def reload_library_from_disk(self):
        library_root = self.require_valid_library_root()
        if not library_root:
            return

        answer = QMessageBox.question(
            self,
            tr("dialog_loading_library"),
            tr("question_reload_library_message"),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return

        self.start_library_reload(library_root)

    def on_mod_selected(self, item):
        """Handle mod selection."""
        if item:
            self.detail_panel.update_mod_details(item.mod_data)

    def closeEvent(self, event):
        candidate_workers = list(self.worker_threads)
        candidate_workers.extend(getattr(self.detail_panel, "preview_threads", []))
        for dialog in self.findChildren(QDialog):
            candidate_workers.extend(getattr(dialog, "title_lookup_threads", {}).values())
            switch_worker = getattr(dialog, "_switch_root_worker", None)
            if switch_worker:
                candidate_workers.append(switch_worker)

        active_workers = {
            id(worker): worker
            for worker in candidate_workers
            if worker is not None and worker.isRunning()
        }
        if active_workers:
            QMessageBox.warning(
                self,
                tr("warning_operations_running_title"),
                tr("warning_operations_running_message"),
            )
            event.ignore()
            return
        event.accept()


def main():
    """Main application entry point."""
    configure_logging()
    app = QApplication(sys.argv)
    
    # Set application properties
    app.setApplicationName("StellarisModManager")
    app.setApplicationDisplayName("")
    app.setApplicationVersion(__version__)
    app.setOrganizationName("project10581")
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
