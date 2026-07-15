from core.workshop_browser_injection import build_queue_cleanup_script, build_queue_sync_script


def test_queue_sync_script_contains_bridge_and_workshop_link_scan():
    script = build_queue_sync_script(
        queued_ids=["123"],
        downloaded_ids=["456"],
        add_tooltip="Add",
        remove_tooltip="Remove",
        downloaded_tooltip="Downloaded",
    )

    assert "__STELLARIS_QUEUE__" in script
    assert "QWebChannel" in script
    assert "sharedfiles/filedetails" in script
    assert "findCardRoot" in script
    assert '"name":"steam-modern"' in script
    assert '"123"' in script
    assert '"456"' in script
    assert "__STELLARIS_WORKSHOP_CONFIG__" not in script


def test_cleanup_script_removes_buttons_and_observer():
    script = build_queue_cleanup_script()

    assert "stellaris-queue-button" in script
    assert "__stellarisQueueObserver" in script
    assert "disconnect" in script


def test_queue_sync_script_serializes_tooltips_as_data():
    script = build_queue_sync_script(
        queued_ids=[],
        downloaded_ids=[],
        add_tooltip='Add "quoted" item',
        remove_tooltip="Remove",
        downloaded_tooltip="Downloaded",
    )

    assert 'Add \\"quoted\\" item' in script
    assert "const config =" in script
