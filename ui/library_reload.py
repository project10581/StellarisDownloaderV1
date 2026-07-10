from core.i18n import tr
from ui.dialogs import LibraryReloadChangesDialog


def format_library_mod_label(mod_data):
    return tr("label_queue_item").format(
        title=(mod_data or {}).get("title") or tr("unknown_mod"),
        workshop_id=(mod_data or {}).get("workshop_id"),
    )


def build_library_reload_log_messages(result):
    changes = (result or {}).get("changes") or {}
    messages = [
        tr("log_loading_library_complete").format(count=(result or {}).get("imported_count", 0)),
        tr("log_loading_library_changes").format(
            added=changes.get("added_count", 0),
            removed=changes.get("removed_count", 0),
        ),
    ]

    added_mods = changes.get("added_mods") or []
    if added_mods:
        added_labels = [format_library_mod_label(mod) for mod in added_mods]
        messages.append(tr("log_loading_library_added").format(ids=", ".join(added_labels)))

    removed_mods = changes.get("removed_mods") or []
    if removed_mods:
        removed_labels = [format_library_mod_label(mod) for mod in removed_mods]
        messages.append(tr("log_loading_library_removed").format(ids=", ".join(removed_labels)))

    return messages


def append_library_reload_change_log(progress_dialog, result):
    for message in build_library_reload_log_messages(result):
        progress_dialog.append_log(message)


def show_library_reload_changes_dialog(result, parent=None):
    changes = (result or {}).get("changes") or {}
    if not changes:
        return

    dialog = LibraryReloadChangesDialog(changes, parent)
    dialog.exec()
