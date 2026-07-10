import logging

from PySide6.QtWidgets import QMessageBox

from core.database import ModDatabase
from core.i18n import tr
from ui.progress import OperationProgressDialog, update_operation_progress
from ui.workers import UpdateCheckThread, UpdateModsThread, retain_worker
from update_dialogs import OutdatedModsDialog


def run_mod_update_check(parent, db_path, worker_threads, refresh_mod_list, silent=False):
    db = ModDatabase(db_path)
    mods = db.list_all_mods()

    if not mods:
        if not silent:
            QMessageBox.information(parent, tr("info_no_mods_title"), tr("info_no_mods_found"))
        return

    progress_dialog = None
    if not silent:
        answer = QMessageBox.question(
            parent,
            tr("question_check_updates_title"),
            tr("question_check_updates_message"),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if answer != QMessageBox.Yes:
            return

        progress_dialog = OperationProgressDialog(tr("dialog_checking_updates"), parent)
        progress_dialog.set_overall(0, len(mods))
        progress_dialog.set_current("Starting update check...")
        progress_dialog.show()

    worker = UpdateCheckThread(mods)
    if progress_dialog:
        worker.progress.connect(
            lambda done, total, current: update_operation_progress(progress_dialog, done, total, current)
        )

    def on_error(error_message):
        if silent:
            logging.error("Automatic mod update check failed: %s", error_message)
            return
        if progress_dialog:
            progress_dialog.close()
        QMessageBox.critical(parent, tr("error_update_check_title"), error_message)

    def on_check_finished(results):
        outdated = [result for result in results if result.get("status") == "update_available"]
        if progress_dialog:
            progress_dialog.append_log(f"Update check complete: {len(outdated)} updates found")
            progress_dialog.mark_done()

        if not outdated:
            if progress_dialog:
                msg_box = QMessageBox(parent)
                msg_box.setWindowTitle(tr("info_all_up_to_date_title"))
                msg_box.setText(tr("info_all_up_to_date_message"))
                msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
                msg_box.finished.connect(lambda _result: progress_dialog.close())
                msg_box.exec()
                refresh_mod_list()
            return

        dialog = OutdatedModsDialog(outdated, parent)
        dialog.exec()

    worker.error.connect(on_error)
    worker.result_ready.connect(on_check_finished)
    retain_worker(worker_threads, worker)
    worker.start()


def run_update_all(parent, db_path, download_root, worker_threads, refresh_mod_list):
    db = ModDatabase(db_path)
    mods = db.list_all_mods()

    if not mods:
        QMessageBox.information(parent, tr("info_no_mods_title"), tr("info_no_mods_found"))
        return

    answer = QMessageBox.question(
        parent,
        tr("question_update_all_mods_title"),
        tr("question_update_all_mods_message"),
        QMessageBox.Yes | QMessageBox.No,
        QMessageBox.No,
    )

    if answer != QMessageBox.Yes:
        return

    progress_dialog = OperationProgressDialog(tr("dialog_checking_updates"), parent)
    progress_dialog.set_overall(0, len(mods))
    progress_dialog.set_current("Starting update check...")
    progress_dialog.show()

    worker_check = UpdateCheckThread(mods)
    worker_check.progress.connect(
        lambda done, total, current: update_operation_progress(progress_dialog, done, total, current)
    )

    def on_check_error(error_message):
        progress_dialog.close()
        QMessageBox.critical(parent, tr("error_update_check_title"), error_message)

    def on_check_finished(results):
        outdated = [result for result in results if result.get("status") == "update_available"]
        if not outdated:
            progress_dialog.append_log("No updates needed.")
            progress_dialog.mark_done()
            QMessageBox.information(parent, tr("info_all_up_to_date_title"), tr("info_all_up_to_date_message"))
            refresh_mod_list()
            progress_dialog.close()
            return

        progress_dialog.append_log(f"{len(outdated)} mods need update. Starting update phase...")
        progress_dialog.mark_done()
        progress_dialog.close()

        workshop_ids = [item["workshop_id"] for item in outdated]
        update_dialog = OperationProgressDialog(tr("dialog_updating_all_outdated_mods"), parent)
        update_dialog.set_overall(0, len(workshop_ids))
        update_dialog.show()

        def update_finished(result):
            update_dialog.append_log(f"Updated: {result['updated']}, Failed: {result['failed']}")
            update_dialog.mark_done()
            refresh_mod_list()

        updater = UpdateModsThread(workshop_ids, download_root, db_path)
        updater.progress.connect(
            lambda done, total, current: update_operation_progress(update_dialog, done, total, current)
        )
        updater.log.connect(update_dialog.append_log)
        updater.error.connect(lambda error_message: QMessageBox.critical(parent, tr("error_update_title"), error_message))
        updater.result_ready.connect(update_finished)
        retain_worker(worker_threads, updater)
        updater.start()

    worker_check.error.connect(on_check_error)
    worker_check.result_ready.connect(on_check_finished)
    retain_worker(worker_threads, worker_check)
    worker_check.start()
