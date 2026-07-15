class WorkshopQueue:
    """Ordered, duplicate-free Workshop queue independent of the Qt UI."""

    def __init__(self):
        self._ids = []
        self._id_set = set()
        self._titles = {}

    @property
    def ids(self) -> tuple[str, ...]:
        return tuple(self._ids)

    def __len__(self) -> int:
        return len(self._ids)

    def __contains__(self, workshop_id: str) -> bool:
        return workshop_id in self._id_set

    def add(self, workshop_id: str, title: str | None = None) -> bool:
        if workshop_id in self._id_set:
            return False
        self._ids.append(workshop_id)
        self._id_set.add(workshop_id)
        if title is not None:
            self._titles[workshop_id] = title
        return True

    def remove(self, workshop_id: str) -> bool:
        if workshop_id not in self._id_set:
            return False
        self._id_set.remove(workshop_id)
        self._ids.remove(workshop_id)
        return True

    def remove_many(self, workshop_ids) -> None:
        remove_ids = set(workshop_ids)
        if not remove_ids:
            return
        self._ids = [workshop_id for workshop_id in self._ids if workshop_id not in remove_ids]
        self._id_set.difference_update(remove_ids)

    def toggle(self, workshop_id: str, title: str | None = None) -> bool:
        if workshop_id in self._id_set:
            self.remove(workshop_id)
            return False
        self.add(workshop_id, title)
        return True

    def clear(self) -> None:
        self._ids.clear()
        self._id_set.clear()

    def set_title(self, workshop_id: str, title: str) -> None:
        self._titles[workshop_id] = title

    def title_for(self, workshop_id: str, default: str) -> str:
        return self._titles.get(workshop_id, default)
