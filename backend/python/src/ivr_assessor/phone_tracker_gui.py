from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .phone_tracker import Interaction, PhoneRecord, PhoneTrackerStore


class PhoneTrackerApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Phone Tracker")
        self.geometry("1380x840")
        self.minsize(1200, 760)
        self.store = PhoneTrackerStore()
        self.filtered_records: list[PhoneRecord] = []
        self.current_phone_number: str | None = None

        self.search_var = tk.StringVar()
        self.status_filter_var = tk.StringVar(value="all")
        self.import_mode_var = tk.StringVar(value="merge")
        self.bulk_status_var = tk.StringVar(value="active")
        self.bulk_preferred_var = tk.StringVar(value="any")
        self.bulk_action_var = tk.StringVar(value="follow_up")
        self.channel_var = tk.StringVar(value="call")
        self.outcome_var = tk.StringVar(value="note")
        self.note_var = tk.StringVar()
        self.alias_var = tk.StringVar()
        self.friendly_name_var = tk.StringVar()
        self.phone_number_var = tk.StringVar()
        self.status_var = tk.StringVar()
        self.preferred_channel_var = tk.StringVar()
        self.next_action_var = tk.StringVar()
        self.notes_text = tk.Text(self, height=6, wrap="word")

        self._build_ui()
        self.refresh_list()

    def _build_ui(self) -> None:
        self.columnconfigure(1, weight=1)
        self.rowconfigure(1, weight=1)

        top = ttk.Frame(self, padding=12)
        top.grid(row=0, column=0, columnspan=2, sticky="ew")
        top.columnconfigure(1, weight=1)

        ttk.Label(top, text="Phone Tracker", font=("Helvetica", 20, "bold")).grid(row=0, column=0, sticky="w")
        ttk.Label(top, text="Organize numbers, statuses, next steps, and history without outbound controls.", foreground="#666").grid(
            row=1, column=0, columnspan=2, sticky="w", pady=(4, 0)
        )

        ttk.Label(top, text="Search").grid(row=0, column=1, sticky="e")
        ttk.Entry(top, textvariable=self.search_var).grid(row=0, column=2, sticky="ew", padx=(8, 0))
        ttk.Button(top, text="Refresh", command=self.refresh_list).grid(row=0, column=3, padx=(8, 0))

        ttk.Label(top, text="Filter").grid(row=1, column=1, sticky="e", pady=(8, 0))
        status_filter = ttk.Combobox(top, textvariable=self.status_filter_var, values=["all", "active", "answered", "left_voicemail", "no_answer", "do_not_contact", "blocked_suspected", "archived"], state="readonly")
        status_filter.grid(row=1, column=2, sticky="ew", padx=(8, 0), pady=(8, 0))
        ttk.Button(top, text="Export CSV", command=self.export_csv).grid(row=1, column=3, padx=(8, 0), pady=(8, 0))

        body = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        body.grid(row=1, column=0, columnspan=2, sticky="nsew")

        left = ttk.Frame(body, padding=10)
        left.columnconfigure(0, weight=1)
        left.rowconfigure(2, weight=1)
        body.add(left, weight=1)

        ttk.Label(left, text="Numbers", font=("Helvetica", 12, "bold")).grid(row=0, column=0, sticky="w")
        self.selection_summary = ttk.Label(left, text="0 selected")
        self.selection_summary.grid(row=0, column=0, sticky="e")

        bulk = ttk.Labelframe(left, text="Bulk Update", padding=10)
        bulk.grid(row=1, column=0, sticky="ew", pady=(8, 10))
        for i in range(2):
            bulk.columnconfigure(i, weight=1)

        ttk.Label(bulk, text="Preferred").grid(row=0, column=0, sticky="w")
        ttk.Combobox(bulk, textvariable=self.bulk_preferred_var, values=["any", "call", "text"], state="readonly").grid(row=0, column=1, sticky="ew", padx=(8, 0))
        ttk.Label(bulk, text="Next action").grid(row=1, column=0, sticky="w", pady=(8, 0))
        ttk.Combobox(bulk, textvariable=self.bulk_action_var, values=["follow_up", "call", "text", "do_not_contact"], state="readonly").grid(row=1, column=1, sticky="ew", padx=(8, 0), pady=(8, 0))
        ttk.Label(bulk, text="Status").grid(row=2, column=0, sticky="w", pady=(8, 0))
        ttk.Combobox(bulk, textvariable=self.bulk_status_var, values=["active", "answered", "left_voicemail", "no_answer", "do_not_contact", "blocked_suspected", "archived"], state="readonly").grid(
            row=2, column=1, sticky="ew", padx=(8, 0), pady=(8, 0)
        )
        ttk.Button(bulk, text="Apply to Selected", command=self.apply_bulk).grid(row=3, column=0, columnspan=2, sticky="ew", pady=(10, 0))

        self.listbox = tk.Listbox(left, selectmode=tk.EXTENDED, exportselection=False, activestyle="dotbox")
        self.listbox.grid(row=2, column=0, sticky="nsew")
        self.listbox.bind("<<ListboxSelect>>", self.on_select)
        scrollbar = ttk.Scrollbar(left, orient="vertical", command=self.listbox.yview)
        self.listbox.configure(yscrollcommand=scrollbar.set)
        scrollbar.grid(row=2, column=1, sticky="ns")

        right = ttk.Frame(body, padding=10)
        right.columnconfigure(1, weight=1)
        body.add(right, weight=3)

        detail = ttk.Labelframe(right, text="Contact Details", padding=12)
        detail.grid(row=0, column=0, sticky="nsew")
        detail.columnconfigure(1, weight=1)

        fields = [
            ("Phone", self.phone_number_var, True),
            ("Friendly name", self.friendly_name_var, False),
            ("Alias", self.alias_var, False),
            ("Status", self.status_var, False),
            ("Preferred channel", self.preferred_channel_var, False),
            ("Next action", self.next_action_var, False),
        ]

        for row, (label, var, readonly) in enumerate(fields):
            ttk.Label(detail, text=label).grid(row=row, column=0, sticky="w", pady=4)
            if readonly:
                ttk.Label(detail, textvariable=var).grid(row=row, column=1, sticky="ew", pady=4)
            else:
                values = None
                if label == "Status":
                    values = ["active", "answered", "left_voicemail", "no_answer", "do_not_contact", "blocked_suspected", "archived"]
                elif label == "Preferred channel":
                    values = ["any", "call", "text"]
                elif label == "Next action":
                    values = ["follow_up", "call", "text", "do_not_contact"]
                if values:
                    ttk.Combobox(detail, textvariable=var, values=values, state="readonly").grid(row=row, column=1, sticky="ew", pady=4)
                else:
                    ttk.Entry(detail, textvariable=var).grid(row=row, column=1, sticky="ew", pady=4)

        ttk.Label(detail, text="Notes").grid(row=6, column=0, sticky="nw", pady=(4, 0))
        self.notes_text.grid(row=6, column=1, sticky="ew", pady=(4, 0))

        actions = ttk.Frame(detail)
        actions.grid(row=7, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        for i in range(5):
            actions.columnconfigure(i, weight=1)
        ttk.Button(actions, text="Save", command=self.save_current).grid(row=0, column=0, sticky="ew")
        ttk.Button(actions, text="Copy Number", command=self.copy_number).grid(row=0, column=1, sticky="ew", padx=4)
        ttk.Button(actions, text="Copy Alias", command=self.copy_alias).grid(row=0, column=2, sticky="ew", padx=4)
        ttk.Button(actions, text="Copy Notes", command=self.copy_notes).grid(row=0, column=3, sticky="ew", padx=4)
        ttk.Button(actions, text="Export Selected CSV", command=self.export_selected_csv).grid(row=0, column=4, sticky="ew")

        interaction = ttk.Labelframe(right, text="Manual Interaction Log", padding=12)
        interaction.grid(row=1, column=0, sticky="nsew", pady=(10, 0))
        interaction.columnconfigure(1, weight=1)

        ttk.Label(interaction, text="Channel").grid(row=0, column=0, sticky="w")
        ttk.Combobox(interaction, textvariable=self.channel_var, values=["call", "text", "note"], state="readonly").grid(row=0, column=1, sticky="ew")
        ttk.Label(interaction, text="Outcome").grid(row=1, column=0, sticky="w", pady=(4, 0))
        ttk.Combobox(interaction, textvariable=self.outcome_var, values=["answered", "left_voicemail", "no_answer", "busy", "failed", "delivered", "undelivered", "blocked_suspected", "note"], state="readonly").grid(
            row=1, column=1, sticky="ew", pady=(4, 0)
        )
        ttk.Label(interaction, text="Note").grid(row=2, column=0, sticky="w", pady=(4, 0))
        ttk.Entry(interaction, textvariable=self.note_var).grid(row=2, column=1, sticky="ew", pady=(4, 0))
        ttk.Button(interaction, text="Log Interaction", command=self.log_interaction).grid(row=3, column=0, columnspan=2, sticky="ew", pady=(8, 0))

        timeline = ttk.Labelframe(right, text="Timeline", padding=12)
        timeline.grid(row=2, column=0, sticky="nsew", pady=(10, 0))
        timeline.columnconfigure(0, weight=1)
        timeline.rowconfigure(0, weight=1)
        self.timeline = tk.Text(timeline, height=14, wrap="word", state="disabled")
        self.timeline.grid(row=0, column=0, sticky="nsew")
        timeline_scroll = ttk.Scrollbar(timeline, orient="vertical", command=self.timeline.yview)
        self.timeline.configure(yscrollcommand=timeline_scroll.set)
        timeline_scroll.grid(row=0, column=1, sticky="ns")

        import_frame = ttk.Frame(right)
        import_frame.grid(row=3, column=0, sticky="ew", pady=(10, 0))
        ttk.Label(import_frame, text="Import mode").grid(row=0, column=0, sticky="w")
        ttk.Combobox(import_frame, textvariable=self.import_mode_var, values=["merge", "replace"], state="readonly").grid(row=0, column=1, sticky="w", padx=(8, 0))
        ttk.Button(import_frame, text="Import CSV", command=self.import_csv).grid(row=0, column=2, sticky="w", padx=(8, 0))

    def refresh_list(self) -> None:
        self.filtered_records = self.store.filtered_records(self.search_var.get(), self.status_filter_var.get())
        self.listbox.delete(0, tk.END)
        for record in self.filtered_records:
            line = f"{record.display_name} | {record.phone_number} | {record.status}"
            self.listbox.insert(tk.END, line)
        self.selection_summary.configure(text=f"{len(self.listbox.curselection())} selected")

    def selected_records(self) -> list[PhoneRecord]:
        indexes = self.listbox.curselection()
        return [self.filtered_records[index] for index in indexes if index < len(self.filtered_records)]

    def active_record(self) -> PhoneRecord | None:
        records = self.selected_records()
        return records[0] if records else None

    def on_select(self, _event: tk.Event) -> None:
        records = self.selected_records()
        self.selection_summary.configure(text=f"{len(records)} selected")
        if records:
            self.load_record(records[0])

    def load_record(self, record: PhoneRecord) -> None:
        self.current_phone_number = record.phone_number
        self.phone_number_var.set(record.phone_number)
        self.friendly_name_var.set(record.friendly_name)
        self.alias_var.set(record.alias)
        self.status_var.set(record.status)
        self.preferred_channel_var.set(record.preferred_channel)
        self.next_action_var.set(record.next_action)
        self.notes_text.delete("1.0", tk.END)
        self.notes_text.insert("1.0", record.notes)
        self.render_timeline(record.phone_number)

    def render_timeline(self, phone_number: str) -> None:
        history = self.store.history_for(phone_number)
        lines = []
        if not history:
            lines.append("No interactions recorded yet.")
        else:
            for item in history:
                lines.append(f"{item.timestamp} | {item.channel} | {item.outcome}")
                if item.note:
                    lines.append(f"  {item.note}")
        self.timeline.configure(state="normal")
        self.timeline.delete("1.0", tk.END)
        self.timeline.insert("1.0", "\n".join(lines))
        self.timeline.configure(state="disabled")

    def save_current(self) -> None:
        if not self.current_phone_number:
            return
        record = self.store.get_record(self.current_phone_number)
        if not record:
            return
        record.friendly_name = self.friendly_name_var.get().strip()
        record.alias = self.alias_var.get().strip()
        record.status = self.status_var.get().strip()
        record.preferred_channel = self.preferred_channel_var.get().strip()
        record.next_action = self.next_action_var.get().strip()
        record.notes = self.notes_text.get("1.0", tk.END).strip()
        self.store.upsert_record(record)
        self.refresh_list()
        self.render_timeline(record.phone_number)

    def apply_bulk(self) -> None:
        selected = self.selected_records()
        if not selected:
            return
        self.store.bulk_update(
            [record.phone_number for record in selected],
            status=self.bulk_status_var.get(),
            preferred_channel=self.bulk_preferred_var.get(),
            next_action=self.bulk_action_var.get(),
        )
        self.refresh_list()
        if self.current_phone_number:
            current = self.store.get_record(self.current_phone_number)
            if current:
                self.load_record(current)

    def log_interaction(self) -> None:
        if not self.current_phone_number:
            return
        interaction = Interaction.create(
            phone_number=self.current_phone_number,
            channel=self.channel_var.get(),
            outcome=self.outcome_var.get(),
            note=self.note_var.get().strip(),
        )
        self.store.add_interaction(interaction)
        self.note_var.set("")
        self.refresh_list()
        record = self.store.get_record(self.current_phone_number)
        if record:
            self.load_record(record)

    def copy_number(self) -> None:
        if self.current_phone_number:
            self.clipboard_clear()
            self.clipboard_append(self.current_phone_number)

    def copy_alias(self) -> None:
        record = self.active_record()
        if record:
            self.clipboard_clear()
            self.clipboard_append(record.alias or record.friendly_name)

    def copy_notes(self) -> None:
        if self.current_phone_number:
            self.clipboard_clear()
            self.clipboard_append(self.notes_text.get("1.0", tk.END).strip())

    def export_csv(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Export phone tracker",
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
        )
        if not path:
            return
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(self.store.export_csv())

    def export_selected_csv(self) -> None:
        selected = self.selected_records()
        if not selected:
            return
        path = filedialog.asksaveasfilename(
            title="Export selected numbers",
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
        )
        if not path:
            return
        with open(path, "w", encoding="utf-8") as handle:
            selected_numbers = {record.phone_number for record in selected}
            subset_interactions = [item for item in self.store.interactions if item.phone_number in selected_numbers]
            handle.write(self.store.export_csv(records=selected, interactions=subset_interactions))

    def import_csv(self) -> None:
        path = filedialog.askopenfilename(
            title="Import phone tracker CSV",
            filetypes=[("CSV", "*.csv"), ("Text", "*.txt"), ("All files", "*.*")],
        )
        if not path:
            return
        with open(path, "r", encoding="utf-8") as handle:
            self.store.import_csv(handle.read(), mode=self.import_mode_var.get())
        self.refresh_list()
        if self.current_phone_number:
            record = self.store.get_record(self.current_phone_number)
            if record:
                self.load_record(record)


def launch() -> None:
    app = PhoneTrackerApp()
    app.mainloop()
