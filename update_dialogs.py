from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from core.i18n import tr
from core.runtime_paths import get_db_path
from core.updater import update_mod
from ui.progress import OperationProgressDialog, update_operation_progress
from ui.workers import UpdateCheckThread, UpdateModsThread, retain_worker


class CheckUpdatesDialog(QDialog):
    """Dialog for checking and selecting mods to update."""

    def __init__(self, mods, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("dialog_check_for_updates"))
        self.setModal(True)
        self.resize(600, 400)

        layout = QVBoxLayout()

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        self.check_button = QPushButton(tr("menu_check_updates"))
        self.check_button.clicked.connect(self.check_updates)
        layout.addWidget(self.check_button)

        self.mod_list_widget = QWidget()
        self.mod_list_layout = QVBoxLayout()
        self.mod_checkboxes = []

        scroll_area = QScrollArea()
        scroll_area.setWidget(self.mod_list_widget)
        scroll_area.setWidgetResizable(True)
        layout.addWidget(scroll_area)

        button_layout = QHBoxLayout()
        select_all_btn = QPushButton(tr("button_select_all"))
        select_all_btn.clicked.connect(self.select_all)
        select_none_btn = QPushButton(tr("button_select_none"))
        select_none_btn.clicked.connect(self.select_none)
        button_layout.addWidget(select_all_btn)
        button_layout.addWidget(select_none_btn)
        layout.addLayout(button_layout)

        self.update_button = QPushButton(tr("button_update_selected_mods"))
        self.update_button.clicked.connect(self.update_selected)
        self.update_button.setEnabled(False)
        layout.addWidget(self.update_button)

        buttons = QDialogButtonBox(QDialogButtonBox.Close, Qt.Horizontal, self)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)
        self.mods = mods
        self.update_results = []

        self.populate_mod_list()

    def populate_mod_list(self):
        for checkbox in self.mod_checkboxes:
            checkbox.setParent(None)
        self.mod_checkboxes.clear()

        for mod in self.mods:
            checkbox = QCheckBox(f"{mod['title'] or 'Unknown'} (ID: {mod['workshop_id']})")
            checkbox.mod_data = mod
            self.mod_list_layout.addWidget(checkbox)
            self.mod_checkboxes.append(checkbox)

        self.mod_list_widget.setLayout(self.mod_list_layout)

    def check_updates(self):
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)

        self.check_thread = UpdateCheckThread(self.mods)
        self.check_thread.result_ready.connect(self.on_check_finished)
        self.check_thread.finished.connect(self.release_check_thread)
        self.check_thread.start()

    def release_check_thread(self):
        worker = self.check_thread
        self.check_thread = None
        worker.deleteLater()

    def on_check_finished(self, results):
        self.progress_bar.setVisible(False)
        self.update_results = results

        for checkbox in self.mod_checkboxes:
            mod_id = checkbox.mod_data["workshop_id"]
            result = next((r for r in results if r["workshop_id"] == mod_id), None)
            if result:
                status = result["status"]
                if status == "update_available":
                    checkbox.setText(f"UPDATE AVAILABLE: {checkbox.mod_data['title'] or 'Unknown'} (ID: {mod_id})")
                    checkbox.setChecked(True)
                elif status == "up_to_date":
                    checkbox.setText(f"Up to date: {checkbox.mod_data['title'] or 'Unknown'} (ID: {mod_id})")
                else:
                    checkbox.setText(f"Check failed: {checkbox.mod_data['title'] or 'Unknown'} (ID: {mod_id})")

        self.update_button.setEnabled(True)

    def select_all(self):
        for checkbox in self.mod_checkboxes:
            checkbox.setChecked(True)

    def select_none(self):
        for checkbox in self.mod_checkboxes:
            checkbox.setChecked(False)

    def update_selected(self):
        selected_mods = [cb.mod_data for cb in self.mod_checkboxes if cb.isChecked()]
        if not selected_mods:
            QMessageBox.information(self, tr("info_no_selection_title"), tr("info_no_selection_update_mods"))
            return

        parent_window = self.parent()
        if not hasattr(parent_window, "require_valid_library_root"):
            QMessageBox.warning(
                self,
                tr("dialog_library_root_required"),
                tr("warning_library_root_validation_unavailable"),
            )
            return

        download_root = parent_window.require_valid_library_root()
        if not download_root:
            return

        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, len(selected_mods))
        self.progress_bar.setValue(0)

        updated = 0
        failed = 0
        for i, mod in enumerate(selected_mods):
            try:
                result = update_mod(mod["workshop_id"], download_root, get_db_path())
                if result.get("status") == "success":
                    updated += 1
                else:
                    failed += 1
            except Exception:
                failed += 1
            self.progress_bar.setValue(i + 1)

        self.progress_bar.setVisible(False)

        QMessageBox.information(
            self,
            tr("info_update_complete_title"),
            tr("info_update_complete_message").format(updated=updated, failed=failed),
        )

        if hasattr(self.parent(), "refresh_mod_list"):
            self.parent().refresh_mod_list()


class OutdatedModsDialog(QDialog):
    """Dialog for selecting and updating outdated mods."""

    def __init__(self, outdated_mods, parent=None):
        super().__init__(parent)
        self.outdated_mods = outdated_mods
        self.parent_window = parent
        self.setWindowTitle(tr("dialog_outdated_mods"))
        self.setMinimumSize(600, 400)
        self.resize(600, 400)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        self.mod_list = QListWidget()
        self.mod_list.setSelectionMode(QListWidget.MultiSelection)
        self.mod_list.itemSelectionChanged.connect(self.update_selection_count)
        layout.addWidget(self.mod_list)

        self.selection_label = QLabel("0/0 mods selected")
        self.selection_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        layout.addWidget(self.selection_label)

        control_layout = QHBoxLayout()
        control_layout.setSpacing(10)

        select_all_btn = QPushButton(tr("button_select_all"))
        select_all_btn.clicked.connect(self.select_all)
        control_layout.addWidget(select_all_btn)

        clear_btn = QPushButton(tr("button_clear"))
        clear_btn.clicked.connect(self.clear_selection)
        control_layout.addWidget(clear_btn)

        self.update_selected_button = QPushButton(tr("button_update_selected"))
        self.update_selected_button.clicked.connect(self.update_selected)
        control_layout.addWidget(self.update_selected_button)

        layout.addLayout(control_layout)

        update_all_layout = QHBoxLayout()
        self.update_all_button = QPushButton(tr("button_update_all"))
        self.update_all_button.clicked.connect(self.update_all)
        self.update_all_button.setMinimumHeight(35)
        update_all_layout.addWidget(self.update_all_button)
        layout.addLayout(update_all_layout)

        close_box = QDialogButtonBox(QDialogButtonBox.Close)
        close_box.rejected.connect(self.reject)
        layout.addWidget(close_box)

        self.populate_mod_list()

    def populate_mod_list(self):
        self.mod_list.clear()
        for mod in self.outdated_mods:
            title = mod.get("latest_title") or str(mod.get("workshop_id"))
            item_text = f"{title} (ID: {mod.get('workshop_id')})"
            item = QListWidgetItem(item_text)
            item.mod_data = mod
            item.setSelected(True)
            self.mod_list.addItem(item)
        self.update_selection_count()

    def update_selection_count(self):
        selected_count = len(self.mod_list.selectedItems())
        total_count = self.mod_list.count()
        self.selection_label.setText(
            tr("label_selection_count").format(selected=selected_count, total=total_count)
        )

    def select_all(self):
        for i in range(self.mod_list.count()):
            self.mod_list.item(i).setSelected(True)

    def clear_selection(self):
        for i in range(self.mod_list.count()):
            self.mod_list.item(i).setSelected(False)

    def update_selected(self):
        selected_items = self.mod_list.selectedItems()
        if not selected_items:
            QMessageBox.information(self, tr("info_no_selection_title"), tr("info_no_outdated_mods_selected"))
            return

        download_root = self.parent_window.require_valid_library_root()
        if not download_root:
            return

        workshop_ids = [item.mod_data["workshop_id"] for item in selected_items]
        self._start_update_worker(workshop_ids, tr("dialog_updating_selected_mods"))

    def update_all(self):
        if not self.outdated_mods:
            QMessageBox.information(self, tr("info_no_mods_title"), tr("info_no_mods_found"))
            return

        download_root = self.parent_window.require_valid_library_root()
        if not download_root:
            return

        workshop_ids = [mod["workshop_id"] for mod in self.outdated_mods]
        self._start_update_worker(workshop_ids, tr("dialog_updating_all_outdated_mods"))

    def _start_update_worker(self, workshop_ids, title):
        download_root = self.parent_window.require_valid_library_root()
        if not download_root:
            return

        progress_dialog = OperationProgressDialog(title, self)
        progress_dialog.show()

        worker = UpdateModsThread(workshop_ids, download_root, self.parent_window.db_path)
        worker.progress.connect(
            lambda done, total, current: update_operation_progress(progress_dialog, done, total, current)
        )
        worker.log.connect(progress_dialog.append_log)
        worker.error.connect(lambda err: QMessageBox.critical(self, tr("error_title"), err))

        def on_finished(result):
            progress_dialog.append_log(
                tr("info_update_complete_message").format(
                    updated=result["updated"],
                    failed=result["failed"],
                )
            )
            progress_dialog.mark_done()
            progress_dialog.close()
            self.parent_window.refresh_mod_list()

        worker.result_ready.connect(on_finished)
        retain_worker(self.parent_window.worker_threads, worker)
        worker.start()
