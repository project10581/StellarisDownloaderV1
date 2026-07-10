from ui.workers import (
    AppUpdateCheckThread,
    AppUpdateDownloadThread,
    DownloadModThread,
    StartupLibraryRefreshThread,
    SwitchLibraryRootThread,
    UpdateCheckThread,
    UpdateModsThread,
)


def test_download_worker_does_not_shadow_qthread_finished_signal():
    assert "result_ready" in DownloadModThread.__dict__
    assert "finished" not in DownloadModThread.__dict__


def test_workers_keep_qthread_finished_signal_for_lifecycle_cleanup():
    worker_types = (
        AppUpdateCheckThread,
        AppUpdateDownloadThread,
        DownloadModThread,
        StartupLibraryRefreshThread,
        SwitchLibraryRootThread,
        UpdateCheckThread,
        UpdateModsThread,
    )

    for worker_type in worker_types:
        assert "result_ready" in worker_type.__dict__
        assert "finished" not in worker_type.__dict__
