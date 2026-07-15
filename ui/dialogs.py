from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from core.i18n import tr


class AppUpdateAvailableDialog(QDialog):
    def __init__(self, current_version, latest_version, release_notes, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("dialog_app_update_available"))
        self.setModal(True)
        self.resize(430, 210)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        version_label = QLabel(
            tr("info_app_update_available_message").format(
                current_version=current_version,
                latest_version=latest_version,
            )
        )
        version_label.setWordWrap(True)
        layout.addWidget(version_label)

        restart_label = QLabel(tr("info_update_will_restart_message"))
        restart_label.setWordWrap(True)
        layout.addWidget(restart_label)

        notes_label = QLabel(tr("info_app_update_notes_label"))
        layout.addWidget(notes_label)

        self.notes_text = QTextEdit()
        self.notes_text.setReadOnly(True)
        self.notes_text.setPlainText((release_notes or "").strip())
        self.notes_text.setMinimumHeight(52)
        self.notes_text.setMaximumHeight(72)
        layout.addWidget(self.notes_text, 1)

        button_layout = QHBoxLayout()
        button_layout.addStretch()
        self.update_button = QPushButton(tr("button_update_now"))
        self.later_button = QPushButton(tr("button_later"))
        button_layout.addWidget(self.update_button)
        button_layout.addWidget(self.later_button)
        layout.addLayout(button_layout)

        self.update_button.clicked.connect(self.accept)
        self.later_button.clicked.connect(self.reject)


class LibraryReloadChangesDialog(QDialog):
    def __init__(self, changes, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("dialog_library_reload_changes"))
        self.setModal(True)
        self.resize(520, 360)

        layout = QVBoxLayout(self)
        summary = QLabel(
            tr("info_library_reload_changes_summary").format(
                removed=changes.get("removed_count", 0),
                added=changes.get("added_count", 0),
            )
        )
        summary.setWordWrap(True)
        layout.addWidget(summary)

        added_mods = changes.get("added_mods") or []
        removed_mods = changes.get("removed_mods") or []

        if removed_mods:
            removed_label = QLabel(tr("label_missing_mods"))
            removed_label.setStyleSheet("font-weight: bold; color: #b00020;")
            layout.addWidget(removed_label)
            removed_list = QListWidget()
            for mod in removed_mods:
                title = mod.get("title") or tr("unknown_mod")
                item = QListWidgetItem(
                    tr("label_queue_item").format(
                        title=title,
                        workshop_id=mod.get("workshop_id"),
                    )
                )
                item.setForeground(Qt.red)
                removed_list.addItem(item)
            layout.addWidget(removed_list, 1)

        if added_mods:
            added_label = QLabel(tr("label_added_mods"))
            added_label.setStyleSheet("font-weight: bold; color: #006400;")
            layout.addWidget(added_label)
            added_list = QListWidget()
            for mod in added_mods:
                title = mod.get("title") or tr("unknown_mod")
                item = QListWidgetItem(
                    tr("label_queue_item").format(
                        title=title,
                        workshop_id=mod.get("workshop_id"),
                    )
                )
                item.setForeground(Qt.darkGreen)
                added_list.addItem(item)
            layout.addWidget(added_list, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)
