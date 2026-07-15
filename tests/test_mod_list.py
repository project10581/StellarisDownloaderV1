from ui.mod_list import get_mod_sort_value, mod_matches_search, sort_mod_records


def test_mod_matches_search_checks_title_and_workshop_id():
    mod = {"title": "Tiny Outliner", "workshop_id": "123456789"}

    assert mod_matches_search(mod, "outline")
    assert mod_matches_search(mod, "456")
    assert not mod_matches_search(mod, "missing")


def test_sort_mod_records_sorts_alphabetically_ascending():
    mods = [
        {"title": "Zoo", "workshop_id": "1"},
        {"title": "alpha", "workshop_id": "2"},
    ]

    assert [mod["workshop_id"] for mod in sort_mod_records(mods, "alphabetical")] == ["2", "1"]


def test_sort_mod_records_sorts_numeric_fields_descending():
    mods = [
        {"workshop_id": "1", "remote_updated_at": 10},
        {"workshop_id": "2", "remote_updated_at": 30},
        {"workshop_id": "3", "remote_updated_at": None},
    ]

    assert get_mod_sort_value(mods[2], "last_workshop_update") == 0
    assert [mod["workshop_id"] for mod in sort_mod_records(mods, "last_workshop_update")] == [
        "2",
        "1",
        "3",
    ]
