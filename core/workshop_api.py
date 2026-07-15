import requests
import logging
from typing import Dict, Iterable, Optional

STEAM_API_URL = "https://api.steampowered.com/ISteamRemoteStorage/GetPublishedFileDetails/v1"


def _parse_file_details(workshop_id: str, file_details: dict) -> Optional[Dict]:
    if not isinstance(file_details, dict) or file_details.get("result") != 1:
        logging.warning(f"Invalid or failed file details result for {workshop_id}: {file_details}")
        return None

    metadata = {
        "title": file_details.get("title"),
        "description": file_details.get("description"),
        "preview_url": file_details.get("preview_url"),
        "creator": file_details.get("creator"),
        "remote_updated_at": file_details.get("time_updated"),
        "time_created": file_details.get("time_created"),
        "tags": file_details.get("tags", []),
        "file_size": file_details.get("file_size"),
    }

    if metadata["title"] is None or metadata["remote_updated_at"] is None:
        logging.warning(f"Missing required fields for {workshop_id}")
        return None

    if metadata["remote_updated_at"]:
        metadata["remote_updated_at"] = int(metadata["remote_updated_at"])
    if metadata["time_created"]:
        metadata["time_created"] = int(metadata["time_created"])

    return metadata


def _chunks(values: list[str], size: int):
    for index in range(0, len(values), size):
        yield values[index:index + size]


def fetch_mod_metadata_batch(workshop_ids: Iterable[str], chunk_size: int = 100) -> Dict[str, Dict]:
    """
    Fetch metadata for multiple mods from Steam Web API.

    Returns:
        Dict mapping Workshop ID to metadata. IDs missing from the result failed lookup.
    """
    normalized_ids = []
    seen = set()
    for workshop_id in workshop_ids:
        workshop_id = str(workshop_id)
        if not workshop_id.isdigit() or workshop_id in seen:
            continue
        normalized_ids.append(workshop_id)
        seen.add(workshop_id)

    if not normalized_ids:
        return {}

    results: Dict[str, Dict] = {}
    for chunk in _chunks(normalized_ids, chunk_size):
        data = {
            "itemcount": len(chunk),
        }
        for index, workshop_id in enumerate(chunk):
            data[f"publishedfileids[{index}]"] = workshop_id

        try:
            logging.info(f"Fetching metadata for {len(chunk)} workshop item(s)")
            response = requests.post(STEAM_API_URL, data=data, timeout=15)
            response.raise_for_status()

            response_data = response.json().get("response", {})
            publishedfiledetails = response_data.get("publishedfiledetails")
            if not isinstance(publishedfiledetails, list):
                logging.warning("No publishedfiledetails returned for metadata batch")
                continue

            for file_details in publishedfiledetails:
                workshop_id = str(file_details.get("publishedfileid") or "")
                metadata = _parse_file_details(workshop_id, file_details)
                if metadata:
                    results[workshop_id] = metadata
                    logging.info(
                        "Successfully fetched metadata for %s: title='%s'",
                        workshop_id,
                        metadata["title"],
                    )
        except requests.exceptions.RequestException as e:
            logging.error(f"Request error fetching metadata batch: {str(e)}")
        except Exception as e:
            logging.error(f"Unexpected error fetching metadata batch: {str(e)}")

    return results


def fetch_mod_metadata(workshop_id: str) -> Optional[Dict]:
    """
    Fetch metadata for a mod from Steam Web API.

    Args:
        workshop_id: Steam Workshop ID

    Returns:
        Optional[Dict]: Dictionary with mod metadata, or None if fetch fails.
    """
    return fetch_mod_metadata_batch([workshop_id]).get(str(workshop_id))
