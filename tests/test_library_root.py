from pathlib import Path
from tempfile import TemporaryDirectory

import core.library_root as library_root
from core.library_root import path_exists_no_follow


def test_path_exists_no_follow_detects_existing_file():
    temp_dir = TemporaryDirectory()
    path = Path(temp_dir.name) / "example.txt"
    path.write_text("ok", encoding="utf-8")

    assert path_exists_no_follow(path)
    temp_dir.cleanup()


def test_path_exists_no_follow_returns_false_for_missing_path():
    temp_dir = TemporaryDirectory()
    path = Path(temp_dir.name) / "missing.txt"

    assert not path_exists_no_follow(path)
    temp_dir.cleanup()


def test_ensure_junction_target_replaces_mismatched_junction_without_directory_check():
    temp_dir = TemporaryDirectory()
    root = Path(temp_dir.name)
    fake_link = root / "281990"
    fake_link.write_text("placeholder", encoding="utf-8")
    target = root / "library"
    calls = []

    original_get_junction_path = library_root.get_junction_path
    original_is_junction = library_root.is_junction
    original_remove_junction = library_root.remove_junction
    original_create_junction = library_root.create_junction
    original_get_junction_target = library_root.get_junction_target

    try:
        library_root.get_junction_path = lambda: fake_link
        library_root.is_junction = lambda path: path == fake_link

        def fake_remove(path):
            calls.append(("remove", path))
            path.unlink()

        def fake_create(link_path, target_path):
            calls.append(("create", link_path, target_path))

        library_root.remove_junction = fake_remove
        library_root.create_junction = fake_create
        library_root.get_junction_target = lambda path: target.resolve()

        assert library_root.ensure_junction_target(str(target)) == fake_link
        assert calls == [
            ("remove", fake_link),
            ("create", fake_link, target.resolve()),
        ]
    finally:
        library_root.get_junction_path = original_get_junction_path
        library_root.is_junction = original_is_junction
        library_root.remove_junction = original_remove_junction
        library_root.create_junction = original_create_junction
        library_root.get_junction_target = original_get_junction_target
        temp_dir.cleanup()


def test_merge_cached_metadata_preserves_values_missing_from_api_refresh():
    previous = [
        {
            "workshop_id": "123",
            "title": "Cached title",
            "description": "Cached description",
            "remote_updated_at": 200,
        }
    ]
    scanned = [
        {
            "workshop_id": "123",
            "title": None,
            "description": None,
            "remote_updated_at": None,
            "content_path": "C:/mods/123",
        }
    ]

    merged = library_root.merge_cached_metadata(previous, scanned)

    assert merged[0]["title"] == "Cached title"
    assert merged[0]["description"] == "Cached description"
    assert merged[0]["remote_updated_at"] == 200
    assert merged[0]["content_path"] == "C:/mods/123"
