from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.i18n import tr
from core.runtime_paths import get_db_path, get_settings_path
from core.settings import SettingsManager
from ui.progress import OperationProgressDialog, update_operation_progress
from ui.library_reload import append_library_reload_change_log, show_library_reload_changes_dialog
from ui.workers import SwitchLibraryRootThread


class SettingsDialog(QDialog):
    """Settings dialog."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("dialog_settings"))
        self.setModal(True)
        self.resize(500, 240)
        self.root_changed = False
        self.root_change_warning_acknowledged = False
        self._suppress_root_change_prompt = False
        self.language_change_notified = False
        self.original_settings = {
            "library_root": "",
            "language": "en",
            "refresh_mod_db_on_startup": False,
            "check_mod_updates_on_startup": False,
            "check_app_updates_on_startup": False,
        }

        layout = QVBoxLayout()

        form_layout = QFormLayout()

        self.library_root_edit = QLineEdit()
        self.library_root_edit.textEdited.connect(self.on_library_root_text_edited)
        browse_button = QPushButton(tr("button_browse"))
        browse_button.clicked.connect(self.browse_library_root)

        root_layout = QHBoxLayout()
        root_layout.addWidget(self.library_root_edit)
        root_layout.addWidget(browse_button)

        form_layout.addRow(tr("label_library_root"), root_layout)

        self.language_combo = QComboBox()
        self.language_combo.addItem(tr("language_english"), "en")
        self.language_combo.addItem(tr("language_simplified_chinese"), "zh")
        self.language_combo.currentIndexChanged.connect(self.on_language_changed)
        form_layout.addRow(tr("label_language"), self.language_combo)

        startup_section_spacer = QWidget()
        startup_section_spacer.setFixedHeight(12)
        form_layout.addRow("", startup_section_spacer)

        startup_options_widget = QWidget()
        startup_options_layout = QVBoxLayout(startup_options_widget)
        startup_options_layout.setContentsMargins(0, 0, 0, 0)
        startup_options_layout.setSpacing(2)

        self.refresh_mod_db_checkbox = QCheckBox(tr("label_refresh_mod_db_on_startup"))
        startup_options_layout.addWidget(self.refresh_mod_db_checkbox)
        self.refresh_mod_db_warning_label = QLabel(tr("label_refresh_mod_db_on_startup_warning"))
        self.refresh_mod_db_warning_label.setWordWrap(True)
        self.refresh_mod_db_warning_label.setStyleSheet("color: red;")
        startup_options_layout.addWidget(self.refresh_mod_db_warning_label)

        startup_options_layout.addSpacing(6)

        self.check_mod_updates_on_startup_checkbox = QCheckBox(tr("label_check_mod_updates_on_startup"))
        startup_options_layout.addWidget(self.check_mod_updates_on_startup_checkbox)
        self.check_mod_updates_on_startup_warning_label = QLabel(tr("label_check_mod_updates_on_startup_warning"))
        self.check_mod_updates_on_startup_warning_label.setWordWrap(True)
        self.check_mod_updates_on_startup_warning_label.setStyleSheet("color: red;")
        startup_options_layout.addWidget(self.check_mod_updates_on_startup_warning_label)

        startup_options_layout.addSpacing(6)

        self.check_app_updates_on_startup_checkbox = QCheckBox(tr("label_check_app_updates_on_startup"))
        startup_options_layout.addWidget(self.check_app_updates_on_startup_checkbox)
        app_update_warning_text = tr("label_check_app_updates_on_startup_warning")
        self.check_app_updates_on_startup_warning_label = QLabel(app_update_warning_text)
        self.check_app_updates_on_startup_warning_label.setWordWrap(True)
        self.check_app_updates_on_startup_warning_label.setVisible(
            bool(app_update_warning_text) and app_update_warning_text != "label_check_app_updates_on_startup_warning"
        )
        startup_options_layout.addWidget(self.check_app_updates_on_startup_warning_label)

        form_layout.addRow(tr("label_startup"), startup_options_widget)

        layout.addLayout(form_layout)

        settings = SettingsManager(get_settings_path())
        current_root = settings.get_library_root()
        if current_root:
            self.original_settings["library_root"] = str(Path(current_root).expanduser().resolve())
            self.library_root_edit.setText(self.original_settings["library_root"])
        current_language = settings.get_language()
        self.original_settings["language"] = current_language
        self.language_combo.setCurrentIndex(max(self.language_combo.findData(current_language), 0))
        refresh_mod_db_on_startup = settings.get_refresh_mod_db_on_startup()
        self.original_settings["refresh_mod_db_on_startup"] = refresh_mod_db_on_startup
        self.refresh_mod_db_checkbox.setChecked(refresh_mod_db_on_startup)
        check_mod_updates_on_startup = settings.get_check_mod_updates_on_startup()
        self.original_settings["check_mod_updates_on_startup"] = check_mod_updates_on_startup
        self.check_mod_updates_on_startup_checkbox.setChecked(check_mod_updates_on_startup)
        check_app_updates_on_startup = settings.get_check_app_updates_on_startup()
        self.original_settings["check_app_updates_on_startup"] = check_app_updates_on_startup
        self.check_app_updates_on_startup_checkbox.setChecked(check_app_updates_on_startup)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Save | QDialogButtonBox.Cancel,
            Qt.Horizontal,
            self,
        )
        buttons.button(QDialogButtonBox.Save).setText(tr("button_save"))
        buttons.button(QDialogButtonBox.Cancel).setText(tr("button_cancel"))
        buttons.accepted.connect(self.save_settings)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)

    def browse_library_root(self):
        if not self.confirm_root_change_intent():
            return

        directory = QFileDialog.getExistingDirectory(self, tr("label_library_root"))
        if directory:
            self.library_root_edit.setText(directory)

    def normalize_root_text(self, root_text):
        root_text = (root_text or "").strip()
        if not root_text:
            return ""
        return str(Path(root_text).expanduser().resolve())

    def get_current_settings_state(self):
        return {
            "library_root": self.normalize_root_text(self.library_root_edit.text()),
            "language": self.language_combo.currentData(),
            "refresh_mod_db_on_startup": self.refresh_mod_db_checkbox.isChecked(),
            "check_mod_updates_on_startup": self.check_mod_updates_on_startup_checkbox.isChecked(),
            "check_app_updates_on_startup": self.check_app_updates_on_startup_checkbox.isChecked(),
        }

    def has_library_root_changed(self):
        return self.get_current_settings_state()["library_root"] != self.original_settings["library_root"]

    def has_settings_changed(self):
        return self.get_current_settings_state() != self.original_settings

    def confirm_root_change_intent(self):
        if not self.original_settings["library_root"]:
            return True
        if self.root_change_warning_acknowledged:
            return True

        response = QMessageBox.warning(
            self,
            tr("dialog_change_library_root"),
            tr("warning_change_library_root_message"),
            QMessageBox.Yes | QMessageBox.Cancel,
            QMessageBox.Cancel,
        )
        if response != QMessageBox.Yes:
            return False

        self.root_change_warning_acknowledged = True
        return True

    def on_library_root_text_edited(self, _text):
        if self._suppress_root_change_prompt:
            return
        if not self.has_library_root_changed():
            return
        if self.confirm_root_change_intent():
            return

        self._suppress_root_change_prompt = True
        self.library_root_edit.setText(self.original_settings["library_root"])
        self._suppress_root_change_prompt = False

    def on_language_changed(self, _index):
        current_language = self.language_combo.currentData()
        if current_language == self.original_settings["language"]:
            return
        if self.language_change_notified:
            return
        QMessageBox.information(
            self,
            tr("dialog_language_changed"),
            tr("info_language_restart_message"),
        )
        self.language_change_notified = True

    def save_settings(self):
        try:
            current_settings = self.get_current_settings_state()
            new_root = current_settings["library_root"]
            new_language = current_settings["language"]
            new_refresh_mod_db_on_startup = current_settings["refresh_mod_db_on_startup"]
            new_check_mod_updates_on_startup = current_settings["check_mod_updates_on_startup"]
            new_check_app_updates_on_startup = current_settings["check_app_updates_on_startup"]
            changed = self.has_settings_changed()
            library_root_changed = new_root != self.original_settings["library_root"]
            language_changed = new_language != self.original_settings["language"]
            refresh_mod_db_on_startup_changed = (
                new_refresh_mod_db_on_startup != self.original_settings["refresh_mod_db_on_startup"]
            )
            check_mod_updates_on_startup_changed = (
                new_check_mod_updates_on_startup != self.original_settings["check_mod_updates_on_startup"]
            )
            check_app_updates_on_startup_changed = (
                new_check_app_updates_on_startup != self.original_settings["check_app_updates_on_startup"]
            )

            if not new_root and self.original_settings["library_root"]:
                QMessageBox.warning(self, tr("warning_invalid_setting_title"), tr("warning_library_root_empty"))
                return

            if changed:
                response = QMessageBox.question(
                    self,
                    tr("dialog_save_changed_settings"),
                    tr("question_save_changed_settings_message"),
                    QMessageBox.Yes | QMessageBox.Cancel,
                    QMessageBox.Yes,
                )
                if response != QMessageBox.Yes:
                    return

            parent_window = self.parent()
            db_path = parent_window.db_path if hasattr(parent_window, "db_path") else get_db_path()
            if library_root_changed and new_root:
                progress_dialog = OperationProgressDialog(tr("dialog_loading_library"), self)
                progress_dialog.set_overall(0, 0)
                progress_dialog.set_current(tr("status_scanning_library_root"))
                progress_dialog.show()

                worker = SwitchLibraryRootThread(get_settings_path(), db_path, new_root)
                worker.progress.connect(
                    lambda done, total, current: update_operation_progress(progress_dialog, done, total, current)
                )
                worker.log.connect(progress_dialog.append_log)

                def on_finished(result):
                    append_library_reload_change_log(progress_dialog, result)
                    progress_dialog.mark_done()
                    self.apply_non_root_settings_changes(
                        new_language,
                        language_changed,
                        new_refresh_mod_db_on_startup,
                        refresh_mod_db_on_startup_changed,
                        new_check_mod_updates_on_startup,
                        check_mod_updates_on_startup_changed,
                        new_check_app_updates_on_startup,
                        check_app_updates_on_startup_changed,
                    )
                    self.root_changed = True
                    self.original_settings = current_settings
                    progress_dialog.close()
                    show_library_reload_changes_dialog(result, self)
                    self.accept()

                def on_error(error_message):
                    progress_dialog.close()
                    QMessageBox.critical(
                        self,
                        tr("error_title"),
                        tr("error_save_settings_message").format(error=error_message),
                    )

                worker.result_ready.connect(on_finished)
                worker.error.connect(on_error)

                def release_worker():
                    self._switch_root_worker = None
                    worker.deleteLater()

                worker.finished.connect(release_worker)
                self._switch_root_worker = worker
                worker.start()
                return

            self.apply_non_root_settings_changes(
                new_language,
                language_changed,
                new_refresh_mod_db_on_startup,
                refresh_mod_db_on_startup_changed,
                new_check_mod_updates_on_startup,
                check_mod_updates_on_startup_changed,
                new_check_app_updates_on_startup,
                check_app_updates_on_startup_changed,
            )
            self.root_changed = library_root_changed
            self.original_settings = current_settings
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, tr("error_title"), tr("error_save_settings_message").format(error=e))

    def apply_non_root_settings_changes(
        self,
        new_language,
        language_changed,
        new_refresh_mod_db_on_startup,
        refresh_mod_db_on_startup_changed,
        new_check_mod_updates_on_startup,
        check_mod_updates_on_startup_changed,
        new_check_app_updates_on_startup,
        check_app_updates_on_startup_changed,
    ):
        settings_manager = SettingsManager(get_settings_path())
        if language_changed:
            settings_manager.set_language(new_language)
        if refresh_mod_db_on_startup_changed:
            settings_manager.set_refresh_mod_db_on_startup(new_refresh_mod_db_on_startup)
        if check_mod_updates_on_startup_changed:
            settings_manager.set_check_mod_updates_on_startup(new_check_mod_updates_on_startup)
        if check_app_updates_on_startup_changed:
            settings_manager.set_check_app_updates_on_startup(new_check_app_updates_on_startup)
