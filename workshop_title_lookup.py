from PySide6.QtCore import QThread, Signal

from core.workshop_titles import resolve_workshop_title


class WorkshopTitleLookupThread(QThread):
    resolved = Signal(str, str)

    def __init__(self, workshop_id, db_path=None):
        super().__init__()
        self.workshop_id = workshop_id
        self.db_path = db_path

    def run(self):
        title = resolve_workshop_title(self.workshop_id, self.db_path)
        self.resolved.emit(self.workshop_id, title)
