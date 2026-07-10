import logging
from typing import Optional, Dict, List
from core.workshop_api import fetch_mod_metadata, fetch_mod_metadata_batch
from core.steamcmd import download_mod
from core.database import ModDatabase


def build_update_check_result(
    workshop_id: str,
    stored_remote_updated_at: Optional[int],
    last_downloaded_at: Optional[int],
    metadata: Optional[Dict],
    local_status: Optional[str] = None,
) -> Dict:
    if not metadata:
        return {
            "workshop_id": workshop_id,
            "stored_remote_updated_at": stored_remote_updated_at,
            "last_downloaded_at": last_downloaded_at,
            "latest_remote_updated_at": None,
            "latest_title": None,
            "status": "failed_check",
            "error": "Failed to fetch metadata from Steam API"
        }

    latest_remote_updated_at = metadata.get("remote_updated_at")
    latest_title = metadata.get("title")

    if latest_remote_updated_at is None:
        status = "failed_check"
        error_msg = "Latest metadata missing remote_updated_at"
    elif local_status == "failed":
        # A failed local download/update must stay retryable even if an older
        # version accidentally recorded the attempt time as a download time.
        status = "update_available"
        error_msg = None
    elif last_downloaded_at is not None:
        status = "update_available" if latest_remote_updated_at > last_downloaded_at else "up_to_date"
        error_msg = None
    elif stored_remote_updated_at is None:
        status = "unknown_state"
        error_msg = "Stored timestamps missing; cannot determine update status"
    elif latest_remote_updated_at > stored_remote_updated_at:
        status = "update_available"
        error_msg = None
    else:
        status = "up_to_date"
        error_msg = None

    return {
        "workshop_id": workshop_id,
        "stored_remote_updated_at": stored_remote_updated_at,
        "last_downloaded_at": last_downloaded_at,
        "latest_remote_updated_at": latest_remote_updated_at,
        "latest_title": latest_title,
        "status": status,
        "error": error_msg if status == "failed_check" else None
    }


def check_mod_for_updates(
    workshop_id: str,
    stored_remote_updated_at: Optional[int],
    last_downloaded_at: Optional[int] = None,
    local_status: Optional[str] = None,
) -> Dict:
    """
    Check if a single mod has updates available.

    Args:
        workshop_id: Steam Workshop ID
        stored_remote_updated_at: Stored remote timestamp from last known metadata
        last_downloaded_at: Stored local download/import timestamp

    Returns:
        Dict with keys:
            - workshop_id: str
            - stored_remote_updated_at: Optional[int]
            - last_downloaded_at: Optional[int]
            - latest_remote_updated_at: Optional[int]
            - status: "up_to_date" | "update_available" | "failed_check"
            - latest_title: Optional[str]
            - error: Optional[str]
    """
    try:
        metadata = fetch_mod_metadata(workshop_id)
        return build_update_check_result(
            workshop_id,
            stored_remote_updated_at,
            last_downloaded_at,
            metadata,
            local_status,
        )
    except Exception as e:
        logging.error(f"Unexpected error checking updates for {workshop_id}: {str(e)}")
        return {
            "workshop_id": workshop_id,
            "stored_remote_updated_at": stored_remote_updated_at,
            "last_downloaded_at": last_downloaded_at,
            "latest_remote_updated_at": None,
            "latest_title": None,
            "status": "failed_check",
            "error": str(e)
        }

def check_all_mods_for_updates(mods: List[Dict]) -> List[Dict]:
    """
    Check all mods for updates.

    Args:
        mods: List of mod records from database

    Returns:
        List of update check results
    """
    metadata_by_id = fetch_mod_metadata_batch([mod["workshop_id"] for mod in mods])
    results = []
    for mod in mods:
        workshop_id = mod['workshop_id']
        stored_remote_updated_at = mod.get('remote_updated_at')
        last_downloaded_at = mod.get('last_downloaded_at')

        results.append(
            build_update_check_result(
                workshop_id,
                stored_remote_updated_at,
                last_downloaded_at,
                metadata_by_id.get(str(workshop_id)),
                mod.get("status"),
            )
        )
    
    return results


def update_mod(workshop_id: str, download_root: str, db_path: str) -> Dict:
    """
    Update a single mod by re-running download and DB refresh.

    Returns result dict from download_mod plus status of existence.
    """
    db = ModDatabase(db_path)
    existing = db.get_mod(workshop_id)
    if not existing:
        return {
            "workshop_id": workshop_id,
            "status": "failed",
            "error": "Mod not tracked in database"
        }

    # Run the normal download logic; it already updates DB via steamcmd.download_mod
    result = download_mod(workshop_id, download_root, db_path)

    # If download failed, preserve old DB title/remote_updated_at via upsert
    if result["status"] != "success":
        # existing db entry has the last known good details
        db.upsert_mod(
            workshop_id=workshop_id,
            app_id=existing["app_id"],
            content_path=existing["content_path"],
            status="failed",
            title=existing.get("title"),
            remote_updated_at=existing.get("remote_updated_at"),
            last_error=result.get("error") or "Update failed",
            last_downloaded_at=existing.get("last_downloaded_at"),
        )

    return result


def update_all_mods(download_root: str, db_path: str) -> Dict:
    """
    Check all tracked mods and update only those needing updates.

    Returns summary counts and per-mod result list.
    """
    db = ModDatabase(db_path)
    mods = db.list_all_mods()
    check_results = check_all_mods_for_updates(mods)

    updated = 0
    skipped = 0
    failed = 0
    details = []

    for check in check_results:
        workshop_id = check["workshop_id"]
        status = check["status"]

        if status == "update_available":
            res = update_mod(workshop_id, download_root, db_path)
            details.append({"workshop_id": workshop_id, "action": "updated", "result": res})
            if res.get("status") == "success":
                updated += 1
            else:
                failed += 1
        elif status == "up_to_date":
            skipped += 1
            details.append({"workshop_id": workshop_id, "action": "skipped", "result": check})
        else:
            failed += 1
            details.append({"workshop_id": workshop_id, "action": "failed_check", "result": check})

    return {
        "updated": updated,
        "skipped": skipped,
        "failed": failed,
        "details": details
    }

