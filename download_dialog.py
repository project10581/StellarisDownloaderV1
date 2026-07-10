from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QPushButton,
    QLineEdit,
    QVBoxLayout,
)

from core.i18n import tr
from core.workshop_ids import extract_workshop_id
from workshop_title_lookup import WorkshopTitleLookupThread


class DownloadFromUrlIdDialog(QDialog):
    """Dialog for entering workshop IDs and queueing downloads."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.setWindowTitle(tr("dialog_download_workshop_mods"))
        self.setModal(True)
        self.resize(520, 400)

        self.queue = []
        self.queue_titles = {}
        self.title_lookup_threads = {}

        main_layout = QVBoxLayout(self)

        input_layout = QHBoxLayout()
        self.workshop_id_edit = QLineEdit()
        self.workshop_id_edit.setPlaceholderText(tr("label_workshop_id_or_url"))
        input_layout.addWidget(self.workshop_id_edit)

        self.add_button = QPushButton(tr("button_add_to_list"))
        self.add_button.clicked.connect(self.add_to_list)
        input_layout.addWidget(self.add_button)

        self.clear_button = QPushButton(tr("button_clear"))
        self.clear_button.clicked.connect(self.clear_input)
        input_layout.addWidget(self.clear_button)

        main_layout.addLayout(input_layout)

        self.download_button = QPushButton(tr("button_download"))
        self.download_button.clicked.connect(self.on_download)
        self.download_button.setMinimumHeight(40)
        main_layout.addWidget(self.download_button)

        queue_controls = QHBoxLayout()
        self.queue_label = QLabel(f"{tr('label_mods_to_download')} (0)")
        queue_controls.addWidget(self.queue_label)

        queue_controls.addStretch()

        self.remove_selected_button = QPushButton(tr("button_remove_selected"))
        self.remove_selected_button.clicked.connect(self.remove_selected)
        queue_controls.addWidget(self.remove_selected_button)

        self.clear_list_button = QPushButton(tr("button_clear_list"))
        self.clear_list_button.clicked.connect(self.clear_list)
        queue_controls.addWidget(self.clear_list_button)

        main_layout.addLayout(queue_controls)

        self.queue_list = QListWidget()
        self.queue_list.setSelectionMode(QListWidget.MultiSelection)
        self.queue_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.queue_list.customContextMenuRequested.connect(self.show_queue_context_menu)
        main_layout.addWidget(self.queue_list)

        bottom_buttons = QDialogButtonBox(QDialogButtonBox.Close)
        bottom_buttons.rejected.connect(self.reject)
        main_layout.addWidget(bottom_buttons)

        self.setLayout(main_layout)

    def update_queue_ui(self):
        self.queue_list.clear()
        for wid in self.queue:
            item = QListWidgetItem(
                tr("label_queue_item").format(
                    title=self.queue_titles.get(wid, tr("unknown_mod")),
                    workshop_id=wid,
                )
            )
            item.setData(Qt.UserRole, wid)
            self.queue_list.addItem(item)
        self.queue_label.setText(f"{tr('label_mods_to_download')} ({len(self.queue)})")

    def ensure_queue_title_async(self, workshop_id):
        if self.queue_titles.get(workshop_id) not in {None, tr("unknown_mod")}:
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
        self.queue_titles[workshop_id] = title or tr("unknown_mod")
        if workshop_id in self.queue:
            self.update_queue_ui()

    def add_to_list(self):
        raw = self.workshop_id_edit.text().strip()
        wid = extract_workshop_id(raw)
        if not wid:
            QMessageBox.warning(
                self,
                tr("warning_invalid_workshop_id_title"),
                tr("warning_invalid_workshop_id_message"),
            )
            return
        if wid in self.queue:
            QMessageBox.information(
                self,
                tr("info_duplicate_title"),
                tr("info_duplicate_message").format(workshop_id=wid),
            )
            self.workshop_id_edit.clear()
            return

        self.queue.append(wid)
        self.queue_titles.setdefault(wid, tr("unknown_mod"))
        self.update_queue_ui()
        self.ensure_queue_title_async(wid)
        self.workshop_id_edit.clear()

    def clear_input(self):
        self.workshop_id_edit.clear()

    def remove_selected(self):
        selections = self.queue_list.selectedItems()
        if not selections:
            return
        for item in selections:
            wid = item.data(Qt.UserRole)
            if wid in self.queue:
                self.queue.remove(wid)
        self.update_queue_ui()

    def clear_list(self):
        self.queue = []
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
            self.queue = [queue_id for queue_id in self.queue if queue_id not in remove_ids]
            self.update_queue_ui()

    def on_download(self):
        current_raw = self.workshop_id_edit.text().strip()
        current_id = extract_workshop_id(current_raw)

        if self.queue and current_id:
            response = QMessageBox.question(
                self,
                tr("question_add_current_input_title"),
                tr("question_add_current_input_message").format(workshop_id=current_id),
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
                QMessageBox.Yes,
            )

            if response == QMessageBox.Cancel:
                return
            if response == QMessageBox.Yes:
                if current_id not in self.queue:
                    self.queue.append(current_id)
                    self.queue_titles.setdefault(current_id, tr("unknown_mod"))
                    self.ensure_queue_title_async(current_id)
                self.update_queue_ui()

        if not self.queue:
            if not current_id:
                QMessageBox.warning(
                    self,
                    tr("warning_no_mod_selected_title"),
                    tr("warning_no_mod_selected_message"),
                )
                return
            self.queue = [current_id]
            self.queue_titles.setdefault(current_id, tr("unknown_mod"))
            self.ensure_queue_title_async(current_id)

        started = self.parent_window.start_download_for_ids(self.queue.copy())
        if not started:
            return
        self.queue = []
        self.update_queue_ui()
        self.workshop_id_edit.clear()
        self.accept()
