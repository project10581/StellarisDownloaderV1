import logging
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QDialog, QMessageBox

from core.app_updater import UpdateError, launch_updater_for_package
from core.i18n import tr
from ui.dialogs import AppUpdateAvailableDialog
from ui.progress import OperationProgressDialog
from ui.workers import AppUpdateCheckThread, AppUpdateDownloadThread, retain_worker


def run_app_update_check(parent, worker_threads, silent=False):
    progress_dialog = None
    if not silent:
        progress_dialog = OperationProgressDialog(tr("dialog_checking_updates"), parent)
        progress_dialog.set_overall(0, 0)
        progress_dialog.set_current(tr("dialog_checking_updates"))
        progress_dialog.show()

    worker = AppUpdateCheckThread()

    def on_finished(result):
        if progress_dialog:
            progress_dialog.mark_done()
            progress_dialog.close()

        release = result["release"]
        if not result["update_available"]:
            if not silent:
                QMessageBox.information(
                    parent,
                    tr("dialog_app_up_to_date"),
                    tr("info_app_is_up_to_date_message"),
                )
            return

        dialog = AppUpdateAvailableDialog(
            result["current_version"],
            result["latest_version"],
            release.notes,
            parent,
        )
        if dialog.exec() == QDialog.Accepted:
            start_app_update_download(parent, worker_threads, release)

    def on_error(error_message):
        if progress_dialog:
            progress_dialog.close()
            QMessageBox.warning(
                parent,
                tr("dialog_app_update_error"),
                tr("error_update_check_failed_message").format(error=error_message),
            )
        else:
            logging.error("Automatic app update check failed: %s", error_message)

    worker.result_ready.connect(on_finished)
    worker.error.connect(on_error)
    retain_worker(worker_threads, worker)
    worker.start()


def start_app_update_download(parent, worker_threads, release):
    progress_dialog = OperationProgressDialog(tr("dialog_downloading_update"), parent)
    progress_dialog.set_overall(0, 0)
    progress_dialog.set_current(tr("status_downloading_update"))
    progress_dialog.show()

    worker = AppUpdateDownloadThread(release)

    def on_progress(downloaded, total):
        progress_dialog.set_overall(downloaded, total)
        if total > 0:
            progress_dialog.set_current(
                tr("status_update_download_progress").format(
                    current_mb=downloaded / (1024 * 1024),
                    total_mb=total / (1024 * 1024),
                )
            )
        else:
            progress_dialog.set_current(tr("status_downloading_update"))

    def on_finished(package_path):
        progress_dialog.append_log(tr("log_update_package_downloaded").format(path=package_path))
        progress_dialog.mark_done()
        try:
            launch_updater_for_package(Path(package_path))
        except UpdateError as exc:
            progress_dialog.close()
            QMessageBox.critical(
                parent,
                tr("dialog_app_update_error"),
                tr("error_updater_launch_failed_message").format(error=exc),
            )
            return

        progress_dialog.close()

        def quit_after_worker_stops():
            if worker.isRunning():
                return
            application = QApplication.instance()
            if application:
                application.quit()

        worker.finished.connect(quit_after_worker_stops)
        QTimer.singleShot(0, quit_after_worker_stops)

    def on_error(error_message):
        progress_dialog.close()
        QMessageBox.warning(
            parent,
            tr("dialog_app_update_error"),
            tr("error_update_download_failed_message").format(error=error_message),
        )

    worker.progress.connect(on_progress)
    worker.result_ready.connect(on_finished)
    worker.error.connect(on_error)
    retain_worker(worker_threads, worker)
    worker.start()
