from ui.library_reload import build_library_reload_log_messages


def test_build_library_reload_log_messages_includes_change_details():
    result = {
        "imported_count": 3,
        "changes": {
            "added_count": 1,
            "removed_count": 1,
            "added_mods": [{"title": "New Mod", "workshop_id": "111"}],
            "removed_mods": [{"title": "Old Mod", "workshop_id": "222"}],
        },
    }

    messages = build_library_reload_log_messages(result)

    assert len(messages) == 4
    assert "3" in messages[0]
    assert "New Mod" in messages[2]
    assert "Old Mod" in messages[3]
