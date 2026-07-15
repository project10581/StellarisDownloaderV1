import os
from tempfile import TemporaryDirectory
from pathlib import Path

import core.file_safety as file_safety
from core.file_safety import resolve_safe_mod_delete_target


def assert_raises_value_error(callback):
    try:
        callback()
    except ValueError:
        return
    raise AssertionError("Expected ValueError")


def test_resolve_safe_mod_delete_target_allows_expected_mod_folder():
    temp_dir = TemporaryDirectory()
    root = Path(temp_dir.name) / "library"
    target = root / "123456789"
    target.mkdir(parents=True)

    expected = Path(os.path.abspath(target))
    assert resolve_safe_mod_delete_target(str(root), str(target), "123456789") == expected
    temp_dir.cleanup()


def test_resolve_safe_mod_delete_target_rejects_other_library_folder():
    temp_dir = TemporaryDirectory()
    root = Path(temp_dir.name) / "library"
    target = root / "987654321"
    target.mkdir(parents=True)

    assert_raises_value_error(
        lambda: resolve_safe_mod_delete_target(str(root), str(target), "123456789")
    )
    temp_dir.cleanup()


def test_resolve_safe_mod_delete_target_rejects_non_numeric_workshop_id():
    temp_dir = TemporaryDirectory()
    root = Path(temp_dir.name) / "library"
    target = root / "not-a-number"
    target.mkdir(parents=True)

    assert_raises_value_error(
        lambda: resolve_safe_mod_delete_target(str(root), str(target), "not-a-number")
    )
    temp_dir.cleanup()


def test_resolve_safe_mod_delete_target_rejects_linked_mod_folder(monkeypatch):
    temp_dir = TemporaryDirectory()
    root = Path(temp_dir.name) / "library"
    target = root / "123456789"
    target.mkdir(parents=True)
    monkeypatch.setattr(file_safety, "_is_reparse_point", lambda path: path == target)

    assert_raises_value_error(
        lambda: resolve_safe_mod_delete_target(str(root), str(target), "123456789")
    )
    temp_dir.cleanup()
