from PySide6.QtWidgets import QListWidgetItem

from core.i18n import tr


NUMERIC_DESCENDING_SORTS = {
    "last_workshop_update",
    "last_download_time",
    "file_size",
}


class ModListItem(QListWidgetItem):
    """List item that keeps the database row attached for selection actions."""

    def __init__(self, mod_data):
        self.mod_data = mod_data
        super().__init__(format_mod_list_item_text(mod_data))


def format_mod_list_item_text(mod_data):
    title = (mod_data or {}).get("title") or tr("unknown_mod")
    workshop_id = (mod_data or {}).get("workshop_id") or ""
    return tr("label_queue_item").format(title=title, workshop_id=workshop_id)


def get_mod_sort_value(mod_data, sort_by):
    if sort_by == "alphabetical":
        return ((mod_data or {}).get("title") or "").lower()
    if sort_by == "last_workshop_update":
        return (mod_data or {}).get("remote_updated_at") or 0
    if sort_by == "last_download_time":
        return (mod_data or {}).get("last_downloaded_at") or 0
    if sort_by == "file_size":
        return (mod_data or {}).get("file_size") or 0
    return 0


def sort_mod_records(mods, sort_by):
    reverse = sort_by in NUMERIC_DESCENDING_SORTS
    return sorted(mods, key=lambda mod: get_mod_sort_value(mod, sort_by), reverse=reverse)


def mod_matches_search(mod_data, search_text):
    normalized_search = (search_text or "").lower()
    if not normalized_search:
        return True

    title = ((mod_data or {}).get("title") or "").lower()
    workshop_id = str((mod_data or {}).get("workshop_id") or "").lower()
    return normalized_search in title or normalized_search in workshop_id
