from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
import csv
import json
from typing import Iterable


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def isoformat(dt: datetime | None) -> str:
    return dt.astimezone(timezone.utc).isoformat() if dt else ""


def parse_dt(value: str) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value)


@dataclass
class PhoneRecord:
    phone_number: str
    friendly_name: str
    alias: str = ""
    status: str = "active"
    preferred_channel: str = "any"
    next_action: str = "follow_up"
    notes: str = ""
    last_interaction_at: str = ""
    last_outcome: str = ""
    created_at: str = field(default_factory=lambda: isoformat(utc_now()))

    @property
    def display_name(self) -> str:
        return self.alias.strip() or self.friendly_name.strip() or self.phone_number

    @property
    def _contact_eligible(self) -> bool:
        return (
            self.status not in {"do_not_contact", "blocked_suspected", "archived"}
            and self.next_action != "do_not_contact"
        )

    @property
    def call_eligible(self) -> bool:
        return self._contact_eligible

    @property
    def text_eligible(self) -> bool:
        return self._contact_eligible


@dataclass
class Interaction:
    timestamp: str
    phone_number: str
    channel: str
    outcome: str
    note: str = ""
    source: str = "manual"

    @classmethod
    def create(cls, phone_number: str, channel: str, outcome: str, note: str = "", source: str = "manual") -> "Interaction":
        return cls(
            timestamp=isoformat(utc_now()),
            phone_number=phone_number,
            channel=channel,
            outcome=outcome,
            note=note,
            source=source,
        )


@dataclass
class PhoneTrackerData:
    records: list[PhoneRecord] = field(default_factory=list)
    interactions: list[Interaction] = field(default_factory=list)


class PhoneTrackerStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or (Path.home() / ".ivr_assessor" / "phone_tracker.json")
        self.data = self._load()

    @property
    def records(self) -> list[PhoneRecord]:
        return self.data.records

    @property
    def interactions(self) -> list[Interaction]:
        return self.data.interactions

    def filtered_records(self, query: str = "", status: str = "all") -> list[PhoneRecord]:
        q = query.strip().lower()
        rows = self.records
        if status != "all":
            rows = [row for row in rows if row.status == status]
        if q:
            rows = [
                row
                for row in rows
                if q in row.phone_number.lower()
                or q in row.friendly_name.lower()
                or q in row.alias.lower()
                or q in row.notes.lower()
            ]
        return sorted(rows, key=lambda row: (row.friendly_name.lower(), row.phone_number))

    def upsert_record(self, record: PhoneRecord) -> None:
        for index, existing in enumerate(self.records):
            if existing.phone_number == record.phone_number:
                self.records[index] = record
                self.save()
                return
        self.records.append(record)
        self.save()

    def add_interaction(self, interaction: Interaction) -> None:
        self.interactions.insert(0, interaction)
        record = self.get_record(interaction.phone_number)
        if record:
            record.last_interaction_at = interaction.timestamp
            record.last_outcome = interaction.outcome
            if interaction.outcome == "left_voicemail":
                record.status = "left_voicemail"
            elif interaction.outcome == "answered":
                record.status = "answered"
            elif interaction.outcome == "blocked_suspected":
                record.status = "blocked_suspected"
            self.upsert_record(record)
        else:
            self.save()

    def get_record(self, phone_number: str) -> PhoneRecord | None:
        for record in self.records:
            if record.phone_number == phone_number:
                return record
        return None

    def history_for(self, phone_number: str) -> list[Interaction]:
        return [item for item in self.interactions if item.phone_number == phone_number]

    def bulk_update(self, phone_numbers: Iterable[str], **changes: str) -> None:
        wanted = set(phone_numbers)
        for index, record in enumerate(self.records):
            if record.phone_number not in wanted:
                continue
            for key, value in changes.items():
                if hasattr(record, key):
                    setattr(record, key, value)
            self.records[index] = record
        self.save()

    def export_csv(
        self,
        records: Iterable[PhoneRecord] | None = None,
        interactions: Iterable[Interaction] | None = None,
    ) -> str:
        records_to_export = list(records) if records is not None else list(self.records)
        interactions_to_export = list(interactions) if interactions is not None else list(self.interactions)
        output = []
        rows = []
        rows.append(
            [
                "type",
                "phone_number",
                "friendly_name",
                "alias",
                "status",
                "preferred_channel",
                "next_action",
                "notes",
                "last_interaction_at",
                "last_outcome",
                "timestamp",
                "channel",
                "outcome",
                "source",
            ]
        )
        for record in records_to_export:
            rows.append(
                [
                    "record",
                    record.phone_number,
                    record.friendly_name,
                    record.alias,
                    record.status,
                    record.preferred_channel,
                    record.next_action,
                    record.notes,
                    record.last_interaction_at,
                    record.last_outcome,
                    "",
                    "",
                    "",
                    "",
                ]
            )
        for interaction in interactions_to_export:
            rows.append(
                [
                    "interaction",
                    interaction.phone_number,
                    "",
                    "",
                    "",
                    "",
                    "",
                    interaction.note,
                    "",
                    "",
                    interaction.timestamp,
                    interaction.channel,
                    interaction.outcome,
                    interaction.source,
                ]
            )

        for row in rows:
            output.append(_csv_row(row))
        return "\n".join(output)

    def import_csv(self, text: str, mode: str = "merge") -> None:
        reader = csv.DictReader(text.splitlines())
        incoming_records: list[PhoneRecord] = []
        incoming_interactions: list[Interaction] = []
        for row in reader:
            row_type = (row.get("type") or "").strip()
            if row_type == "record":
                incoming_records.append(
                    PhoneRecord(
                        phone_number=row.get("phone_number", "").strip(),
                        friendly_name=row.get("friendly_name", "").strip(),
                        alias=row.get("alias", "").strip(),
                        status=row.get("status", "active").strip() or "active",
                        preferred_channel=row.get("preferred_channel", "any").strip() or "any",
                        next_action=row.get("next_action", "follow_up").strip() or "follow_up",
                        notes=row.get("notes", "").strip(),
                        last_interaction_at=row.get("last_interaction_at", "").strip(),
                        last_outcome=row.get("last_outcome", "").strip(),
                    )
                )
            elif row_type == "interaction":
                incoming_interactions.append(
                    Interaction(
                        timestamp=row.get("timestamp", isoformat(utc_now())),
                        phone_number=row.get("phone_number", "").strip(),
                        channel=row.get("channel", "note").strip() or "note",
                        outcome=row.get("outcome", "note").strip() or "note",
                        note=row.get("notes", "").strip() or row.get("note", "").strip(),
                        source=row.get("source", "manual").strip() or "manual",
                    )
                )

        if mode == "replace":
            if incoming_records:
                self.data.records = incoming_records
            if incoming_interactions:
                self.data.interactions = incoming_interactions
        else:
            existing_by_number = {record.phone_number: record for record in self.records}
            for record in incoming_records:
                existing_by_number[record.phone_number] = record
            self.data.records = list(existing_by_number.values())
            self.data.interactions = incoming_interactions + self.interactions

        self.save()

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "records": [asdict(record) for record in self.records],
            "interactions": [asdict(item) for item in self.interactions],
        }
        self.path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    def _load(self) -> PhoneTrackerData:
        if not self.path.exists():
            return PhoneTrackerData(records=_seed_records())

        payload = json.loads(self.path.read_text(encoding="utf-8"))
        records = [PhoneRecord(**item) for item in payload.get("records", [])]
        interactions = [Interaction(**item) for item in payload.get("interactions", [])]
        if not records:
            records = _seed_records()
        return PhoneTrackerData(records=records, interactions=interactions)


def _csv_row(values: list[str]) -> str:
    from io import StringIO

    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(values)
    return buffer.getvalue().strip("\r\n")


def _seed_records() -> list[PhoneRecord]:
    seed = [
        ("+16624384811", "Twilio #1 - Tishomingo MS"),
        ("+16174207443", "Twilio #2 - Everett MA"),
        ("+16079004530", "Twilio #3 - McGraw NY"),
        ("+15715688394", "Twilio #4 - US General"),
        ("+17743586607", "Twilio #5 - Harwich MA"),
        ("+14454474885", "Twilio #6 - US General"),
        ("+13636661972", "Twilio #7 - Hempstead NY"),
        ("+15086257682", "Twilio #8 - Hopkinton MA"),
        ("+12027513252", "Twilio #9 - Washington DC"),
        ("+18282376302", "Twilio #10 - Garden City NC"),
        ("+14472515797", "Twilio #11 - US General"),
        ("+18579714037", "Twilio #12 - Charlestown MA"),
        ("+14705172162", "Twilio #13 - Villa Rica GA"),
        ("+12186585128", "Twilio #14 - Denham MN"),
    ]
    return [
        PhoneRecord(phone_number=number, friendly_name=name, alias=name)
        for number, name in seed
    ]
