from core.database import ModDatabase
from core.i18n import tr
from core.workshop_api import fetch_mod_metadata


def resolve_workshop_title(workshop_id: str, db_path: str | None = None) -> str:
    if db_path:
        mod_record = ModDatabase(db_path).get_mod(workshop_id)
        if mod_record and mod_record.get("title"):
            return mod_record["title"]

    metadata = fetch_mod_metadata(workshop_id)
    if metadata and metadata.get("title"):
        return metadata["title"]
    return tr("unknown_mod")
