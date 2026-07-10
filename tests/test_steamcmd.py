from pathlib import Path

from core.steamcmd import _record_failed_attempt, classify_steamcmd_output


def test_classify_steamcmd_output_success():
    assert classify_steamcmd_output("Success. Downloaded item 123456") == "success"


def test_classify_steamcmd_output_failure():
    assert classify_steamcmd_output("ERROR! Download item failed") == "failed"


def test_classify_steamcmd_output_defaults_to_failed():
    assert classify_steamcmd_output("SteamCMD finished without a clear result") == "failed"


class FakeDatabase:
    def __init__(self, existing):
        self.existing = existing
        self.upsert_kwargs = None

    def get_mod(self, _workshop_id):
        return self.existing

    def upsert_mod(self, **kwargs):
        self.upsert_kwargs = kwargs
        return True


def test_failed_attempt_preserves_last_successful_download_time():
    database = FakeDatabase(
        {
            "workshop_id": "123",
            "app_id": 281990,
            "content_path": "C:/mods/123",
            "last_downloaded_at": 100,
        }
    )

    _record_failed_attempt(database, "123", Path("C:/mods/123"), "download failed")

    assert database.upsert_kwargs["last_downloaded_at"] == 100
    assert database.upsert_kwargs["status"] == "failed"


def test_initial_failed_download_is_not_added_to_database():
    database = FakeDatabase(None)

    _record_failed_attempt(database, "123", Path("C:/mods/123"), "download failed")

    assert database.upsert_kwargs is None
