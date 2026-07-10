import os
import stat
from pathlib import Path


def _absolute_without_resolving(path: str | Path) -> Path:
    return Path(os.path.abspath(os.path.expanduser(str(path))))


def _is_reparse_point(path: Path) -> bool:
    try:
        if path.is_symlink():
            return True
        is_junction = getattr(path, "is_junction", None)
        if is_junction and is_junction():
            return True
        attributes = getattr(path.lstat(), "st_file_attributes", 0)
        return bool(attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))
    except FileNotFoundError:
        return False


def resolve_safe_mod_delete_target(
    library_root: str,
    content_path: str,
    workshop_id: str,
) -> Path:
    if not workshop_id or not str(workshop_id).isdigit():
        raise ValueError("Refusing to delete mod files without a valid numeric Workshop ID.")
    if not library_root:
        raise ValueError("Library root is not configured.")
    if not content_path:
        raise ValueError("Mod content path is not configured.")

    root = _absolute_without_resolving(library_root)
    target = _absolute_without_resolving(content_path)
    expected = root / str(workshop_id)

    if os.path.normcase(str(target)) != os.path.normcase(str(expected)):
        raise ValueError(f"Refusing to delete unexpected mod path: {target}")
    if target == root:
        raise ValueError("Refusing to delete the library root.")
    if target.parent.resolve() != root.resolve():
        raise ValueError(f"Refusing to delete path outside the library root: {target}")
    if _is_reparse_point(target):
        raise ValueError(f"Refusing to recursively delete a linked mod path: {target}")

    return target
