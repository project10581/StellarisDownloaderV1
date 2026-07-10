from core.workshop_queue import WorkshopQueue


def test_queue_preserves_order_and_rejects_duplicates():
    queue = WorkshopQueue()

    assert queue.add("123", "First")
    assert queue.add("456", "Second")
    assert not queue.add("123", "Duplicate")
    assert queue.ids == ("123", "456")
    assert queue.title_for("123", "Unknown") == "First"


def test_queue_toggle_remove_many_and_clear():
    queue = WorkshopQueue()
    queue.add("123")
    queue.add("456")
    queue.add("789")

    assert not queue.toggle("456")
    assert queue.toggle("999")
    queue.remove_many(["123", "789"])
    assert queue.ids == ("999",)

    queue.clear()
    assert queue.ids == ()
    assert len(queue) == 0
