from core.updater import build_update_check_result


def test_build_update_check_result_detects_available_update_from_download_time():
    result = build_update_check_result(
        "123",
        stored_remote_updated_at=100,
        last_downloaded_at=100,
        metadata={"remote_updated_at": 200, "title": "A Mod"},
    )

    assert result["status"] == "update_available"
    assert result["latest_title"] == "A Mod"


def test_build_update_check_result_reports_up_to_date():
    result = build_update_check_result(
        "123",
        stored_remote_updated_at=200,
        last_downloaded_at=300,
        metadata={"remote_updated_at": 200, "title": "A Mod"},
    )

    assert result["status"] == "up_to_date"


def test_build_update_check_result_reports_failed_metadata_fetch():
    result = build_update_check_result(
        "123",
        stored_remote_updated_at=200,
        last_downloaded_at=300,
        metadata=None,
    )

    assert result["status"] == "failed_check"


def test_failed_local_mod_remains_retryable_after_newer_attempt_timestamp():
    result = build_update_check_result(
        "123",
        stored_remote_updated_at=200,
        last_downloaded_at=300,
        metadata={"remote_updated_at": 200, "title": "A Mod"},
        local_status="failed",
    )

    assert result["status"] == "update_available"
