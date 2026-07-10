import shutil
from typing import Dict

from core.database import ModDatabase
from core.file_safety import resolve_safe_mod_delete_target


def delete_mod_files_and_record(
    db_path: str,
    library_root: str,
    mod_data: Dict,
) -> bool:
    workshop_id = (mod_data or {}).get("workshop_id")
    content_path = (mod_data or {}).get("content_path")
    target = resolve_safe_mod_delete_target(library_root, content_path, workshop_id)

    if target.exists():
        if target.is_dir():
            shutil.rmtree(target)
        else:
            target.unlink()

    return ModDatabase(db_path).delete_mod(workshop_id)
