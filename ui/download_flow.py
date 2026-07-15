from PySide6.QtWidgets import QMessageBox

from core.i18n import tr
from ui.progress import OperationProgressDialog
from ui.workers import DownloadModThread, retain_worker


def start_download_sequence(
    parent,
    db_path,
    worker_threads,
    download_root,
    workshop_ids,
    refresh_mod_list,
    finished_callback=None,
):
    download_queue = list(workshop_ids)
    if not download_queue:
        QMessageBox.warning(parent, tr("info_no_mods_title"), tr("warning_no_mod_selected_message"))
        return False

    total_count = len(download_queue)
    download_results = []
    sequence_finished = False

    progress_dialog = OperationProgressDialog(tr("dialog_downloading_mods"), parent)
    progress_dialog.set_overall(0, total_count)
    progress_dialog.set_current("Starting downloads...")
    progress_dialog.show()

    def finish_sequence():
        nonlocal sequence_finished
        if sequence_finished:
            return
        sequence_finished = True

        success = sum(1 for result in download_results if result.get("status") == "success")
        failed = len(download_results) - success
        progress_dialog.mark_done()
        refresh_mod_list()

        msg_box = QMessageBox(parent)
        msg_box.setWindowTitle(tr("question_download_summary_title"))
        msg_box.setText(tr("question_download_summary_message").format(success=success, failed=failed))
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg_box.finished.connect(lambda _result: progress_dialog.close())
        if finished_callback:
            msg_box.finished.connect(lambda _result: finished_callback())
        msg_box.exec()

    def start_next():
        if not download_queue:
            finish_sequence()
            return

        current = download_queue.pop(0)
        progress_dialog.set_current(f"Downloading {current}")
        progress_dialog.append_log(f"Start downloading {current}")

        worker = DownloadModThread(current, download_root, db_path)
        worker.started_signal.connect(lambda workshop_id: progress_dialog.set_current(f"Downloading {workshop_id}"))
        worker.progress.connect(progress_dialog.append_log)

        result_received = False

        def record_result(result, workshop_id=current):
            nonlocal result_received
            if result_received:
                return
            result_received = True
            download_results.append(result)
            progress_dialog.set_overall(len(download_results), total_count)
            if result.get("status") == "success":
                progress_dialog.append_log(f"{workshop_id} downloaded successfully")
            else:
                progress_dialog.append_log(
                    f"{workshop_id} download failed: {result.get('error', 'Unknown')}"
                )
            start_next()

        def record_error(error_message, workshop_id=current):
            nonlocal result_received
            if result_received:
                return
            result_received = True
            download_results.append(
                {
                    "status": "failed",
                    "workshop_id": workshop_id,
                    "error": error_message,
                }
            )
            progress_dialog.set_overall(len(download_results), total_count)
            progress_dialog.append_log(f"{workshop_id} error: {error_message}")
            start_next()

        worker.result_ready.connect(record_result)
        worker.error.connect(record_error)
        retain_worker(worker_threads, worker)
        worker.start()

    start_next()
    return True
