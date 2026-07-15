from PySide6.QtCore import QThread, Signal

from core.app_updater import check_for_updates, download_release_asset
from core.i18n import tr
from core.library_root import rebuild_database_from_library_root, switch_library_root
from core.steamcmd import download_mod
from core.updater import check_all_mods_for_updates, update_mod


def retain_worker(worker_threads, worker):
    """Keep a worker alive until QThread has actually stopped, then release it."""
    worker_threads.append(worker)

    def release_worker():
        if worker in worker_threads:
            worker_threads.remove(worker)
        worker.deleteLater()

    worker.finished.connect(release_worker)
    return worker


class AppUpdateCheckThread(QThread):
    result_ready = Signal(dict)
    error = Signal(str)

    def run(self):
        try:
            self.result_ready.emit(check_for_updates())
        except Exception as e:
            self.error.emit(str(e))


class AppUpdateDownloadThread(QThread):
    progress = Signal(int, int)
    result_ready = Signal(str)
    error = Signal(str)

    def __init__(self, release_info):
        super().__init__()
        self.release_info = release_info

    def run(self):
        try:
            path = download_release_asset(
                self.release_info,
                progress_callback=lambda current, total: self.progress.emit(current, total),
            )
            self.result_ready.emit(str(path))
        except Exception as e:
            self.error.emit(str(e))


class UpdateCheckThread(QThread):
    progress = Signal(int, int, str)
    result_ready = Signal(list)
    error = Signal(str)

    def __init__(self, mods):
        super().__init__()
        self.mods = mods

    def run(self):
        try:
            total = len(self.mods)
            for index, mod in enumerate(self.mods, start=1):
                self.progress.emit(index, total, f"Queued {mod['workshop_id']}")
            results = check_all_mods_for_updates(self.mods)
            self.result_ready.emit(results)
        except Exception as e:
            self.error.emit(str(e))


class DownloadModThread(QThread):
    started_signal = Signal(str)
    progress = Signal(str)
    result_ready = Signal(dict)
    error = Signal(str)

    def __init__(self, workshop_id, download_root, db_path):
        super().__init__()
        self.workshop_id = workshop_id
        self.download_root = download_root
        self.db_path = db_path

    def run(self):
        try:
            self.started_signal.emit(self.workshop_id)
            self.progress.emit(f"Starting download for {self.workshop_id}")
            result = download_mod(self.workshop_id, self.download_root, self.db_path)
            self.progress.emit(f"Download completed for {self.workshop_id} ({result.get('status')})")
            self.result_ready.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class PreviewImageThread(QThread):
    image_loaded = Signal(str, object)
    load_failed = Signal(str, str)

    def __init__(self, preview_url):
        super().__init__()
        self.preview_url = preview_url

    def run(self):
        try:
            import urllib.request

            request = urllib.request.Request(
                self.preview_url,
                headers={"User-Agent": "StellarisModManager/1.0"},
            )
            max_bytes = 10 * 1024 * 1024
            with urllib.request.urlopen(request, timeout=10) as response:
                image_data = response.read(max_bytes + 1)
            if len(image_data) > max_bytes:
                raise ValueError("Preview image is too large.")
            self.image_loaded.emit(self.preview_url, image_data)
        except Exception as e:
            self.load_failed.emit(self.preview_url, str(e))


class UpdateModsThread(QThread):
    progress = Signal(int, int, str)
    log = Signal(str)
    result_ready = Signal(dict)
    error = Signal(str)

    def __init__(self, workshop_ids, download_root, db_path):
        super().__init__()
        self.workshop_ids = workshop_ids
        self.download_root = download_root
        self.db_path = db_path

    def run(self):
        try:
            total = len(self.workshop_ids)
            updated = 0
            failed = 0
            details = []
            for index, workshop_id in enumerate(self.workshop_ids, start=1):
                self.progress.emit(index, total, f"Updating {workshop_id}")
                self.log.emit(f"Updating {workshop_id}...")
                try:
                    result = update_mod(workshop_id, self.download_root, self.db_path)
                    details.append({"workshop_id": workshop_id, "result": result})
                    if result.get("status") == "success":
                        updated += 1
                        self.log.emit(f"{workshop_id} updated successfully")
                    else:
                        failed += 1
                        err = result.get("error", "unknown")
                        self.log.emit(f"{workshop_id} update failed: {err}")
                except Exception as e:
                    failed += 1
                    self.log.emit(f"{workshop_id} update raised exception: {e}")
                self.progress.emit(index, total, f"Completed {workshop_id}")
            self.result_ready.emit({"updated": updated, "failed": failed, "details": details})
        except Exception as e:
            self.error.emit(str(e))


class StartupLibraryRefreshThread(QThread):
    progress = Signal(int, int, str)
    log = Signal(str)
    result_ready = Signal(dict)
    error = Signal(str)

    def __init__(self, db_path, library_root):
        super().__init__()
        self.db_path = db_path
        self.library_root = library_root

    def run(self):
        try:
            def on_progress(current, total, token):
                if token == "scan_started":
                    current_text = tr("status_scanning_library_root")
                else:
                    current_text = tr("status_loading_library_mod").format(workshop_id=token)
                self.progress.emit(current, total, current_text)

            def on_log(workshop_id):
                self.log.emit(tr("status_loading_library_mod").format(workshop_id=workshop_id))

            result = rebuild_database_from_library_root(
                self.db_path,
                self.library_root,
                progress_callback=on_progress,
                log_callback=on_log,
            )
            self.log.emit(tr("log_loading_library_rebuilding_database"))
            self.result_ready.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class SwitchLibraryRootThread(QThread):
    progress = Signal(int, int, str)
    log = Signal(str)
    result_ready = Signal(dict)
    error = Signal(str)

    def __init__(self, settings_path, db_path, new_library_root):
        super().__init__()
        self.settings_path = settings_path
        self.db_path = db_path
        self.new_library_root = new_library_root

    def run(self):
        try:
            def on_progress(current, total, token):
                if token == "scan_started":
                    current_text = tr("status_scanning_library_root")
                else:
                    current_text = tr("status_loading_library_mod").format(workshop_id=token)
                self.progress.emit(current, total, current_text)

            def on_log(workshop_id):
                self.log.emit(tr("status_loading_library_mod").format(workshop_id=workshop_id))

            result = switch_library_root(
                self.settings_path,
                self.db_path,
                self.new_library_root,
                progress_callback=on_progress,
                log_callback=on_log,
            )
            self.log.emit(tr("log_loading_library_rebuilding_database"))
            self.result_ready.emit(result)
        except Exception as e:
            self.error.emit(str(e))
