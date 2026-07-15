from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QProgressBar, QTextEdit, QVBoxLayout

from core.i18n import tr


class OperationProgressDialog(QDialog):
    """Reusable progress dialog for background operations."""

    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumSize(500, 320)

        self.layout = QVBoxLayout(self)

        self.overall_label = QLabel(tr("label_overall_progress"))
        self.layout.addWidget(self.overall_label)

        self.overall_bar = QProgressBar()
        self.overall_bar.setRange(0, 100)
        self.layout.addWidget(self.overall_bar)

        self.current_label = QLabel(tr("label_current_item"))
        self.layout.addWidget(self.current_label)

        self.current_bar = QProgressBar()
        self.current_bar.setRange(0, 0)
        self.layout.addWidget(self.current_bar)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setPlainText("")
        self.layout.addWidget(self.log_text)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Close)
        self.button_box.button(QDialogButtonBox.Close).setEnabled(False)
        self.button_box.rejected.connect(self.close)
        self.layout.addWidget(self.button_box)

        self.completed = False

    def set_overall(self, current, total):
        if total > 0:
            self.overall_bar.setRange(0, total)
            self.overall_bar.setValue(current)
            self.overall_label.setText(tr("label_overall_value").format(current=current, total=total))
        else:
            self.overall_bar.setRange(0, 0)
            self.overall_label.setText(tr("label_overall_processing"))

    def set_current(self, text):
        self.current_label.setText(tr("label_current_value").format(text=text))

    def append_log(self, message):
        self.log_text.append(message)

    def mark_done(self):
        self.current_bar.setRange(0, 1)
        self.current_bar.setValue(1)
        self.append_log(tr("log_operation_completed"))
        self.button_box.button(QDialogButtonBox.Close).setEnabled(True)
        self.completed = True


def update_operation_progress(progress_dialog, done, total, current):
    progress_dialog.set_overall(done, total)
    progress_dialog.set_current(current)
