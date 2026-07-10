import pytest

from core.app_updater import (
    UpdateError,
    compare_versions,
    get_safe_asset_filename,
    normalize_version_tag,
)


def test_normalize_version_tag_strips_leading_v():
    assert normalize_version_tag("v1.6.0") == "1.6.0"
    assert normalize_version_tag("1.6.0") == "1.6.0"


def test_compare_versions_handles_missing_patch_parts():
    assert compare_versions("1.6", "1.6.0") == 0
    assert compare_versions("1.6.0", "1.7.0") < 0
    assert compare_versions("1.10.0", "1.9.9") > 0


def test_update_asset_filename_rejects_paths_and_non_zip_files():
    assert get_safe_asset_filename("StellarisModManager1.6.1.zip") == "StellarisModManager1.6.1.zip"
    with pytest.raises(UpdateError):
        get_safe_asset_filename("../StellarisModManager.zip")
    with pytest.raises(UpdateError):
        get_safe_asset_filename("StellarisModManager.exe")
