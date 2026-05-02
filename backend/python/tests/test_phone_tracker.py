from __future__ import annotations

from pathlib import Path

from ivr_assessor.phone_tracker import Interaction, PhoneRecord, PhoneTrackerData, PhoneTrackerStore


def test_save_and_reload_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "tracker.json"
    store = PhoneTrackerStore(path=path)
    store.data = PhoneTrackerData(
        records=[
            PhoneRecord(
                phone_number="+15551230001",
                friendly_name="Example Contact",
                alias="Example",
                status="active",
                preferred_channel="text",
                next_action="follow_up",
                notes="Original note",
            )
        ],
        interactions=[
            Interaction.create(
                phone_number="+15551230001",
                channel="text",
                outcome="delivered",
                note="Sent test message",
            )
        ],
    )
    store.save()

    reloaded = PhoneTrackerStore(path=path)
    record = reloaded.get_record("+15551230001")

    assert record is not None
    assert record.friendly_name == "Example Contact"
    assert record.alias == "Example"
    assert record.notes == "Original note"
    assert reloaded.history_for("+15551230001")[0].outcome == "delivered"


def test_export_and_import_csv_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "tracker.json"
    store = PhoneTrackerStore(path=path)
    store.data = PhoneTrackerData(
        records=[
            PhoneRecord(
                phone_number="+15551230002",
                friendly_name="CSV Contact",
                alias="CSV",
                status="answered",
                preferred_channel="call",
                next_action="follow_up",
                notes="Needs follow-up",
                last_interaction_at="2026-04-23T12:00:00+00:00",
                last_outcome="answered",
            )
        ],
        interactions=[
            Interaction(
                timestamp="2026-04-23T12:00:00+00:00",
                phone_number="+15551230002",
                channel="call",
                outcome="answered",
                note="Reached voicemail",
                source="manual",
            )
        ],
    )

    csv_text = store.export_csv()
    imported = PhoneTrackerStore(path=tmp_path / "imported.json")
    imported.data = PhoneTrackerData(records=[], interactions=[])
    imported.import_csv(csv_text, mode="replace")

    record = imported.get_record("+15551230002")
    assert record is not None
    assert record.friendly_name == "CSV Contact"
    assert record.status == "answered"
    assert imported.history_for("+15551230002")[0].outcome == "answered"


def test_add_interaction_updates_record_status(tmp_path: Path) -> None:
    store = PhoneTrackerStore(path=tmp_path / "tracker.json")
    store.data = PhoneTrackerData(
        records=[
            PhoneRecord(
                phone_number="+15551230003",
                friendly_name="Status Contact",
            )
        ],
        interactions=[],
    )

    store.add_interaction(
        Interaction.create(
            phone_number="+15551230003",
            channel="call",
            outcome="left_voicemail",
            note="Left a voicemail",
        )
    )

    record = store.get_record("+15551230003")
    assert record is not None
    assert record.status == "left_voicemail"
    assert record.last_outcome == "left_voicemail"
