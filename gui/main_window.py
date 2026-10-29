"""Tkinter interface for scanning, reviewing and organizing files."""

from __future__ import annotations

import queue
import threading
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
import tkinter as tk

from analytics.reports import build_report, format_bytes
from core.duplicate_detector import DuplicateDetector, DuplicateGroup
from core.organizer import FileOrganizer, OrganizationItem
from core.scanner import FileInfo, FileScanner, ScanResult
from storage.history_manager import HistoryManager

try:
    import matplotlib
    matplotlib.use("TkAgg")
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
    MATPLOTLIB_AVAILABLE = True
except Exception:
    MATPLOTLIB_AVAILABLE = False


class MainWindow:
    """Own the widgets and coordinate background work with a UI event queue."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Smart File Organizer & Duplicate Detector")
        self.root.geometry("1180x760")
        self.root.minsize(900, 600)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self.project_dir = Path(__file__).resolve().parents[1]
        self.history = HistoryManager(self.project_dir / "data" / "scan_history.json")
        self.scanner = FileScanner()
        self.detector = DuplicateDetector()
        self.organizer = FileOrganizer()
        self.events: queue.Queue[tuple] = queue.Queue()
        self.busy = False
        self.current_root: Path | None = None
        self.files: list[FileInfo] = []
        self.duplicates: list[DuplicateGroup] = []
        self.warnings: list[str] = []
        self.preview: list[OrganizationItem] = []
        self.chart_canvas = None

        self._build_ui()
        self._load_history()
        self.root.after(100, self._poll_events)

    def _build_ui(self) -> None:
        top = ttk.Frame(self.root, padding=(12, 10))
        top.pack(fill="x")
        ttk.Label(top, text="Selected folder:").pack(side="left")
        self.folder_var = tk.StringVar(value="No folder selected")
        ttk.Label(top, textvariable=self.folder_var, width=70).pack(side="left", padx=(6, 10), fill="x", expand=True)
        self.choose_button = ttk.Button(top, text="Choose Folder…", command=self._choose_folder)
        self.choose_button.pack(side="left", padx=4)
        self.scan_button = ttk.Button(top, text="Scan Folder", command=self._scan_selected)
        self.scan_button.pack(side="left", padx=4)
        self.organize_button = ttk.Button(top, text="Prepare Organization", command=self._prepare_organization, state="disabled")
        self.organize_button.pack(side="left", padx=4)

        self.status_var = tk.StringVar(value="Choose a folder to begin. Scanning never moves files.")
        ttk.Label(self.root, textvariable=self.status_var, relief="sunken", anchor="w", padding=(8, 5)).pack(side="bottom", fill="x")

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=(0, 8))
        self.dashboard_tab = ttk.Frame(self.notebook, padding=12)
        self.inventory_tab = ttk.Frame(self.notebook, padding=8)
        self.duplicates_tab = ttk.Frame(self.notebook, padding=8)
        self.organize_tab = ttk.Frame(self.notebook, padding=8)
        self.analytics_tab = ttk.Frame(self.notebook, padding=8)
        self.history_tab = ttk.Frame(self.notebook, padding=8)
        for tab, title in ((self.dashboard_tab, "Dashboard"), (self.inventory_tab, "File Inventory"),
                           (self.duplicates_tab, "Duplicates"), (self.organize_tab, "Organize Preview"),
                           (self.analytics_tab, "Storage Analytics"), (self.history_tab, "Scan History")):
            self.notebook.add(tab, text=title)
        self._build_dashboard()
        self.inventory_tree = self._tree(self.inventory_tab, ("name", "extension", "size", "category", "modified", "path"),
                                         ("Name", "Extension", "Size", "Category", "Modified", "Path"),
                                         (190, 80, 95, 100, 170, 390))
        self.duplicate_tree = self._tree(self.duplicates_tab, ("kind", "size", "path"),
                                         ("Group / File", "Size", "Path"), (140, 100, 700))
        self._build_organize_tab()
        self._build_analytics_tab()
        self._build_history_tab()

    def _build_dashboard(self) -> None:
        ttk.Label(self.dashboard_tab, text="Scan dashboard", font=("Segoe UI", 17, "bold")).pack(anchor="w", pady=(0, 12))
        cards = ttk.Frame(self.dashboard_tab)
        cards.pack(fill="x")
        self.metric_vars: dict[str, tk.StringVar] = {}
        metrics = (("Files scanned", "0"), ("Total size", "0 B"), ("Duplicate groups", "0"),
                   ("Potential reclaimable storage", "0 B"))
        for title, initial in metrics:
            card = ttk.LabelFrame(cards, text=title, padding=14)
            card.pack(side="left", fill="both", expand=True, padx=(0, 8))
            value = tk.StringVar(value=initial)
            self.metric_vars[title] = value
            ttk.Label(card, textvariable=value, font=("Segoe UI", 16, "bold")).pack(anchor="w")
        ttk.Label(self.dashboard_tab, text="The reclaimable figure estimates extra bytes in duplicate groups beyond one retained copy.",
                  wraplength=900).pack(anchor="w", pady=18)
        self.warning_var = tk.StringVar(value="Warnings: none")
        ttk.Label(self.dashboard_tab, textvariable=self.warning_var, wraplength=1000).pack(anchor="w", pady=4)

    def _tree(self, parent, columns, headings, widths):
        frame = ttk.Frame(parent)
        frame.pack(fill="both", expand=True)
        tree = ttk.Treeview(frame, columns=columns, show="headings")
        yscroll = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        xscroll = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        for column, heading, width in zip(columns, headings, widths):
            tree.heading(column, text=heading)
            tree.column(column, width=width, minwidth=60, anchor="w", stretch=column in {"path"})
        tree.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)
        return tree

    def _build_organize_tab(self) -> None:
        bar = ttk.Frame(self.organize_tab)
        bar.pack(fill="x", pady=(0, 8))
        ttk.Label(bar, text="Review every destination and status. Files move only after confirmation.").pack(side="left", fill="x", expand=True)
        self.confirm_button = ttk.Button(bar, text="Confirm and Move", command=self._confirm_organization, state="disabled")
        self.confirm_button.pack(side="right", padx=4)
        self.cancel_button = ttk.Button(bar, text="Cancel Preview", command=self._cancel_preview, state="disabled")
        self.cancel_button.pack(side="right", padx=4)
        self.organize_tree = self._tree(self.organize_tab, ("source", "destination", "category", "status"),
                                        ("Source path", "Destination path", "Category", "Operation status"),
                                        (360, 390, 100, 220))

    def _build_analytics_tab(self) -> None:
        self.analytics_summary = tk.StringVar(value="Scan a folder to see category totals.")
        ttk.Label(self.analytics_tab, textvariable=self.analytics_summary, padding=6).pack(anchor="w")
        self.analytics_tree = ttk.Treeview(self.analytics_tab, columns=("category", "files", "size"),
                                           show="headings", height=7)
        for column, heading, width in (("category", "Category", 220), ("files", "File count", 130), ("size", "Storage size", 180)):
            self.analytics_tree.heading(column, text=heading)
            self.analytics_tree.column(column, width=width, anchor="w")
        self.analytics_tree.pack(fill="x", padx=6, pady=(0, 8))
        self.chart_frame = ttk.Frame(self.analytics_tab)
        self.chart_frame.pack(fill="both", expand=True)
        if not MATPLOTLIB_AVAILABLE:
            ttk.Label(self.chart_frame, text="Matplotlib is not available. Install dependencies from requirements.txt.").pack(expand=True)

    def _build_history_tab(self) -> None:
        bar = ttk.Frame(self.history_tab)
        bar.pack(fill="x", pady=(0, 8))
        ttk.Label(bar, text="Saved snapshots show what a scan found at that time.").pack(side="left", fill="x", expand=True)
        ttk.Button(bar, text="View Selected Details", command=self._show_history_details).pack(side="right")
        self.history_tree = self._tree(self.history_tab, ("timestamp", "root", "files", "size", "groups", "reclaimable"),
                                       ("Scan time", "Selected folder", "Files", "Total size", "Duplicate groups", "Potential reclaimable"),
                                       (170, 400, 70, 110, 120, 170))

    def _choose_folder(self) -> None:
        selected = filedialog.askdirectory(title="Select a folder to scan", mustexist=True)
        if selected:
            self.current_root = Path(selected)
            self.folder_var.set(str(self.current_root))
            self.preview = []
            self._render_organization([])
            self.files = []
            self.duplicates = []
            self.warnings = []
            self._render_scan()
            self.status_var.set("Folder selected. Select Scan Folder to inspect its files.")

    def _scan_selected(self) -> None:
        if self.current_root is None:
            messagebox.showinfo("Select a folder", "Choose a folder before scanning.", parent=self.root)
            return
        self._start_scan(self.current_root)

    def _start_scan(self, root: Path, preserve_preview: bool = False) -> None:
        if self.busy:
            return
        self.current_root = root
        self.folder_var.set(str(root))
        if not preserve_preview:
            self.preview = []
            self._render_organization([])
        self.files = []
        self.duplicates = []
        self.warnings = []
        self._render_scan()
        self._set_busy(True, "Scanning files and checking duplicate content…")

        def work() -> None:
            try:
                scan = self.scanner.scan(root)
                duplicate_result = self.detector.find_duplicates(scan.files)
                self.events.put(("scan_done", scan, duplicate_result.groups, scan.warnings + duplicate_result.warnings))
            except Exception as error:
                self.events.put(("error", "Scan failed", str(error)))

        threading.Thread(target=work, name="file-scan", daemon=True).start()

    def _set_busy(self, busy: bool, message: str | None = None) -> None:
        self.busy = busy
        state = "disabled" if busy else "normal"
        self.choose_button.configure(state=state)
        self.scan_button.configure(state=state)
        self.organize_button.configure(state="disabled" if busy or not self.files else "normal")
        self.confirm_button.configure(state="disabled" if busy or not self.preview or not any(x.status == "Ready" for x in self.preview) else "normal")
        self.cancel_button.configure(state="disabled" if busy or not self.preview else "normal")
        if message:
            self.status_var.set(message)

    def _poll_events(self) -> None:
        try:
            while True:
                event = self.events.get_nowait()
                if event[0] == "scan_done":
                    _, scan, groups, warnings = event
                    self._accept_scan(scan, groups, warnings)
                    self._set_busy(False)
                elif event[0] == "organization_done":
                    _, results = event
                    self.preview = results
                    self._render_organization(results)
                    moved = sum(item.status == "Moved" for item in results)
                    failed = sum(item.status.startswith(("Failed", "Skipped")) for item in results)
                    self._set_busy(False, f"Organization finished: {moved} moved; {failed} failed or skipped. Refreshing scan…")
                    if self.current_root:
                        self._start_scan(self.current_root, preserve_preview=True)
                elif event[0] == "error":
                    _, title, details = event
                    self._set_busy(False, title)
                    messagebox.showerror(title, details, parent=self.root)
        except queue.Empty:
            pass
        self.root.after(100, self._poll_events)

    def _accept_scan(self, scan: ScanResult, groups: list[DuplicateGroup], warnings: list[str]) -> None:
        self.files = scan.files
        self.duplicates = groups
        self.warnings = warnings
        self.current_root = Path(scan.root)
        self._render_scan()
        self._set_busy(False, f"Scan complete: {len(self.files)} files; {len(groups)} duplicate groups.")
        record = self._history_record(scan, groups, warnings)
        try:
            self.history.save(record)
        except (OSError, ValueError) as error:
            self.status_var.set(f"Scan complete, but history could not be saved: {error}")
        self._load_history()

    def _history_record(self, scan: ScanResult, groups: list[DuplicateGroup], warnings: list[str]) -> dict:
        report = build_report(scan.files, groups)
        return {
            "scan_timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
            "root_path": scan.root,
            **report,
            "category_summaries": {
                category: {"file_count": count, "size_bytes": report["category_sizes"].get(category, 0)}
                for category, count in report["category_counts"].items()
            },
            "duplicate_groups": [
                {"sha256": group.sha256, "file_count": group.file_count, "size_bytes": group.size,
                 "potential_reclaimable_bytes": group.reclaimable_bytes,
                 "files": [{"path": path, "size_bytes": group.size} for path in group.paths]}
                for group in groups
            ],
            "warnings": warnings,
        }

    def _render_scan(self) -> None:
        report = build_report(self.files, self.duplicates)
        self.metric_vars["Files scanned"].set(str(report["total_file_count"]))
        self.metric_vars["Total size"].set(format_bytes(report["total_size"]))
        self.metric_vars["Duplicate groups"].set(str(report["duplicate_group_count"]))
        self.metric_vars["Potential reclaimable storage"].set(format_bytes(report["potential_reclaimable_bytes"]))
        self.warning_var.set("Warnings: " + ("; ".join(self.warnings[:4]) if self.warnings else "none"))

        self._clear_tree(self.inventory_tree)
        for item in self.files:
            self.inventory_tree.insert("", "end", values=(item.name, item.extension, format_bytes(item.size), item.category,
                                                               item.modified_at, item.path))
        self._clear_tree(self.duplicate_tree)
        if not self.duplicates:
            self.duplicate_tree.insert("", "end", values=("No duplicate groups", "", ""))
        for index, group in enumerate(self.duplicates, 1):
            group_id = self.duplicate_tree.insert("", "end", values=(f"Group {index} ({group.file_count} files)", format_bytes(group.size), group.sha256))
            for path in group.paths:
                self.duplicate_tree.insert(group_id, "end", values=("Duplicate file", format_bytes(group.size), path))
            self.duplicate_tree.item(group_id, open=True)
        category_count = len(report["category_counts"])
        self.analytics_summary.set(
            f"{report['total_file_count']} files · {format_bytes(report['total_size'])} · {category_count} categories · "
            f"{report['duplicate_group_count']} duplicate groups · {report['duplicate_file_count']} participating files"
        )
        self._clear_tree(self.analytics_tree)
        if not report["category_counts"]:
            self.analytics_tree.insert("", "end", values=("No files in this scan", "0", "0 B"))
        for category in sorted(report["category_counts"]):
            self.analytics_tree.insert("", "end", values=(category, report["category_counts"][category],
                                                              format_bytes(report["category_sizes"].get(category, 0))))
        self._render_chart(report)
        self.organize_button.configure(state="normal" if self.files and not self.busy else "disabled")

    def _render_chart(self, report: dict) -> None:
        if not MATPLOTLIB_AVAILABLE:
            return
        if self.chart_canvas is not None:
            self.chart_canvas.get_tk_widget().destroy()
        figure = Figure(figsize=(8, 4.7), dpi=100, tight_layout=True)
        axis = figure.add_subplot(111)
        category_sizes = report["category_sizes"]
        if category_sizes:
            categories = list(category_sizes)
            values = [category_sizes[category] / (1024 * 1024) for category in categories]
            axis.bar(categories, values, color="#4472C4")
            axis.tick_params(axis="x", rotation=25)
        else:
            axis.text(0.5, 0.5, "No files in this scan", ha="center", va="center", transform=axis.transAxes)
            axis.set_xticks([])
        axis.set_title("Storage by file category")
        axis.set_xlabel("File category")
        axis.set_ylabel("Storage size (MiB)")
        self.chart_canvas = FigureCanvasTkAgg(figure, master=self.chart_frame)
        self.chart_canvas.draw()
        self.chart_canvas.get_tk_widget().pack(fill="both", expand=True)

    def _prepare_organization(self) -> None:
        if self.busy or not self.current_root:
            return
        self.preview = self.organizer.create_preview(self.current_root, self.files)
        self._render_organization(self.preview)
        self.notebook.select(self.organize_tab)
        ready = sum(item.status == "Ready" for item in self.preview)
        self.status_var.set(f"Preview ready: {ready} files can be moved. Review destinations before confirming.")
        self._set_busy(False)

    def _render_organization(self, items: list[OrganizationItem]) -> None:
        self._clear_tree(self.organize_tree)
        for item in items:
            self.organize_tree.insert("", "end", values=(item.source, item.destination, item.category, item.status))
        self.confirm_button.configure(state="normal" if items and any(x.status == "Ready" for x in items) and not self.busy else "disabled")
        self.cancel_button.configure(state="normal" if items and not self.busy else "disabled")

    def _confirm_organization(self) -> None:
        if self.busy or not self.current_root or not self.preview:
            return
        ready = sum(item.status == "Ready" for item in self.preview)
        if not messagebox.askyesno("Confirm file organization", f"Move {ready} file(s) into Organized by category?", parent=self.root):
            return
        preview = list(self.preview)
        root = self.current_root
        self._set_busy(True, "Moving files safely…")

        def work() -> None:
            try:
                self.events.put(("organization_done", self.organizer.execute(root, preview)))
            except Exception as error:
                self.events.put(("error", "Organization failed", str(error)))

        threading.Thread(target=work, name="file-organization", daemon=True).start()

    def _cancel_preview(self) -> None:
        if self.busy:
            return
        self.preview = []
        self._render_organization([])
        self.status_var.set("Organization preview cancelled. No files were moved.")

    def _load_history(self) -> None:
        records, warnings = self.history.load_with_warnings()
        self._clear_tree(self.history_tree)
        for index, record in enumerate(reversed(records)):
            values = (record.get("scan_timestamp", ""), record.get("root_path", ""), record.get("total_file_count", ""),
                      format_bytes(int(record.get("total_size", 0))), record.get("duplicate_group_count", 0),
                      format_bytes(int(record.get("potential_reclaimable_bytes", 0))))
            self.history_tree.insert("", "end", iid=f"history_{len(records) - index - 1}", values=values)
        if warnings:
            self.status_var.set(warnings[0])

    def _show_history_details(self) -> None:
        selection = self.history_tree.selection()
        if not selection:
            messagebox.showinfo("Scan history", "Select a saved scan snapshot first.", parent=self.root)
            return
        records = self.history.load()
        try:
            index = int(selection[0].removeprefix("history_"))
            record = records[index]
        except (ValueError, IndexError):
            return
        detail = [f"Scanned: {record.get('scan_timestamp', 'unknown')}", f"Folder: {record.get('root_path', 'unknown')}",
                  f"Files: {record.get('total_file_count', 0)}", f"Total size: {format_bytes(int(record.get('total_size', 0)))}",
                  f"Duplicate groups: {record.get('duplicate_group_count', 0)}",
                  f"Potential reclaimable: {format_bytes(int(record.get('potential_reclaimable_bytes', 0)))}"]
        for group_no, group in enumerate(record.get("duplicate_groups", []), 1):
            detail.append(f"\nGroup {group_no} ({group.get('file_count', 0)} files):")
            detail.extend(f"  {file.get('path', '')} ({format_bytes(int(file.get('size_bytes', 0)))})" for file in group.get("files", []))
        if record.get("warnings"):
            detail.append("\nWarnings:")
            detail.extend(f"  {warning}" for warning in record["warnings"])
        messagebox.showinfo("Saved scan snapshot", "\n".join(detail), parent=self.root)

    @staticmethod
    def _clear_tree(tree: ttk.Treeview) -> None:
        children = tree.get_children("")
        if children:
            tree.delete(*children)

    def _on_close(self) -> None:
        if self.busy:
            messagebox.showinfo("Operation in progress", "Please wait for the current file operation to finish before closing.", parent=self.root)
            return
        self.root.destroy()
