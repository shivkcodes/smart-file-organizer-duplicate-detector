# Smart File Organizer & Duplicate Detector

A local Windows desktop mini project built with Python. It scans a folder, groups files by extension-based category, detects equal file content with SHA-256, previews organization destinations, and shows storage summaries. Scanning, duplicate detection, and previewing do not modify files. A move occurs only after the user reviews the preview and confirms it.

## Problem statement

Folders often collect documents, images, code, media, and repeated copies without a clear structure. Finding a particular file or estimating how much space repeated copies occupy can take time. This application creates a searchable inventory, reports exact content duplicates, and offers a reviewable way to place files into category folders.

## Objectives and scope

- Scan a selected local directory recursively and capture file metadata.
- Classify files by extension into Documents, Images, Videos, Audio, Archives, Code, or Others.
- Detect equal content using file size as a first filter and SHA-256 as the content comparison.
- Preview proposed paths and status before moving anything.
- Calculate file counts and storage totals from the scan, and retain local JSON scan snapshots.
- Keep file operations local. The application does not inspect file contents for classification, delete files, use cloud services, or send data over the internet.

The project handles ordinary files and common filesystem errors, but cannot make a changing filesystem fully race-free. A file may change between the final validation and the actual copy, and a power loss during a cross-volume copy can leave an incomplete target. The implementation uses exclusive target creation, removes partial copies on caught errors, preserves the source until copying completes, and reports failures. Always review the preview and keep normal backups.

## Features

- Recursive scanner that skips symbolic links and the root's generated `Organized` directory.
- Inventory with file name, extension, size, absolute path, modification time, and category.
- SHA-256 duplicate groups. Same-size files with different hashes are not duplicates. Unreadable or changing candidates are reported as warnings.
- Organization preview with source, destination, category, and status. Existing names get a numbered suffix; destination files are never intentionally overwritten.
- Dashboard metrics, category storage bar chart, duplicate counts, and potential reclaimable storage. Reclaimable storage means the bytes in extra copies beyond one copy per duplicate group; it is an estimate, not guaranteed recovered space.
- Local scan history at `data/scan_history.json`, including duplicate paths and scan warnings. History entries are snapshots from scan time, not a live view.
- Background scan, hashing, and organization work to keep the Tkinter window responsive.

## Technologies

- Python 3.12 or 3.13 (the core is also exercised with Python 3.14 in the current development environment)
- Tkinter and ttk for the desktop UI
- `pathlib`, `os`, and `shutil` for filesystem work
- `hashlib` for SHA-256
- `json` for local scan history
- Matplotlib for the embedded analytics chart
- `unittest` and `tempfile` for automated tests

Matplotlib installs its normal runtime dependencies, including NumPy; this project does not use NumPy directly. The execution host used for this build had Python 3.14.7 only, so the local `.venv` and test run use 3.14.7. Python 3.12/3.13 were not available for direct testing here; the project uses Python 3.10+ syntax, and the selected Matplotlib release supports Python 3.11 and later.

## Project structure

```text
.
├── main.py
├── requirements.txt
├── README.md
├── gui/
│   └── main_window.py
├── core/
│   ├── scanner.py
│   ├── organizer.py
│   ├── duplicate_detector.py
│   └── file_categories.py
├── analytics/
│   └── reports.py
├── storage/
│   └── history_manager.py
├── data/
│   └── scan_history.json
└── tests/
    ├── test_scanner.py
    ├── test_organizer.py
    ├── test_duplicates.py
    ├── test_history.py
    └── test_reports.py
```

The packages are at the workspace root so the application starts with `python main.py` from this folder.

## Windows setup (PowerShell)

Install Python 3.12 or 3.13 from python.org. The regular Windows installer should include Tcl/Tk; if `tkinter` is unavailable, rerun the installer and enable the Tcl/Tk option. From the project directory:

```powershell
py -3.12 --version
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -c "import tkinter; import matplotlib; print('Tk', tkinter.TkVersion, 'Matplotlib', matplotlib.__version__)"
```

If you use Python 3.13, replace `py -3.12` with `py -3.13`. If PowerShell blocks activation, enable script activation for the current PowerShell process with `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`, then activate again. If Matplotlib installation fails, first upgrade pip in the activated environment; use a current 64-bit Python installer so pip can select a compatible wheel. Matplotlib is the only third-party dependency.

The ready-to-run virtual environment in this workspace was created with Python 3.14.7 because that was the only installed interpreter. On this computer you can use it directly with `\.venv\Scripts\python.exe main.py`; on a fresh Windows setup, use the Python 3.12 or 3.13 commands above.

## Run the application

With the virtual environment active, from the project directory:

```powershell
python main.py
```

Choose a folder, click **Scan Folder**, and review the Dashboard, File Inventory, Duplicates, Storage Analytics, and Scan History tabs. To organize, click **Prepare Organization**, inspect all paths and statuses in **Organize Preview**, then select **Confirm and Move** and accept the confirmation dialog. **Cancel Preview** leaves the source files unchanged. Files are placed under `<selected folder>\Organized\<Category>\`.

## Tests

Run the complete automated suite from the project folder:

```powershell
python -m unittest discover -s tests -v
```

The tests make temporary files and folders. They cover scanning and invalid paths, categories, organized-folder exclusion, duplicate hashing and reclaimable bytes, read-only preview/cancel behavior, confirmed moves and collisions, stale inputs, history save/load and malformed data, and report calculations.

## How the application works

`FileScanner` walks a chosen directory and reads metadata without loading whole files. The scan excludes symbolic links and the generated `Organized` folder. `DuplicateDetector` first groups metadata by byte size, so a file whose size is unique needs no hash. It then streams same-size candidates through SHA-256 in chunks. A matching hash is evidence of equal content for this application; file names alone are never used as duplicate proof.

`FileOrganizer` makes a proposed destination for every scanned file without creating folders or moving data. The GUI displays those proposals and waits for the user's explicit confirmation. On confirmation, each source and destination is checked again. The move copies to an exclusively created destination, preserves metadata, and removes the source only after a successful copy; independent failures are recorded while later items continue.

`build_report` calculates summary values from scan records and duplicate groups. The GUI shows those values and uses Matplotlib to chart storage size by category. `HistoryManager` stores scan-time summaries and detailed duplicate paths in JSON. It writes a temporary file beside the history file and replaces the saved file only after the new JSON has been written, reducing the chance of truncating history during a failed save.

## Main classes and functions

- `FileScanner.scan(root)`: validates a folder and returns `ScanResult` with `FileInfo` metadata and warnings.
- `classify_extension(extension)`: maps an extension to a category in one dedicated module.
- `DuplicateDetector.find_duplicates(files)`: filters by size, streams candidate files through SHA-256, and returns groups and warnings.
- `DuplicateGroup.reclaimable_bytes`: counts all bytes beyond one retained file in that group.
- `FileOrganizer.create_preview(root, files)`: creates a read-only list of source/destination operations.
- `FileOrganizer.execute(root, preview)`: revalidates and performs confirmed operations, returning a status for each.
- `build_report(files, duplicate_groups)`: calculates dashboard and chart totals without GUI dependencies.
- `HistoryManager.load()` / `save(record)`: reads snapshots and atomically updates the local JSON history.
- `MainWindow`: builds the ttk interface and transfers long-running work to worker threads; Tk widgets are updated on the main thread through a queue.

## MCA Semester 1 viva preparation

1. **What problem does your project solve?** — It makes a large folder easier to inspect by listing and categorizing files, showing exact-content duplicates, and offering a controlled way to place files into category folders.
2. **What is a file scanner?** — It is code that visits folders and records selected properties of files. This project records names, extensions, sizes, paths, modification times, and categories.
3. **Why use `pathlib`?** — `Path` objects make joining paths and checking files clearer than manually concatenating path strings, and they work across operating systems.
4. **How does recursive scanning work?** — The scanner visits a folder and its child folders. It prunes the generated output folder and does not follow symbolic links, reducing repeated paths and accidental traversal elsewhere.
5. **How are files categorized?** — The program reads the extension, such as `.pdf` or `.jpg`, and looks it up in a mapping. It does not infer category from file contents.
6. **Why group by file size before hashing?** — Equal files must have equal sizes. A unique-size file cannot have a same-content partner in the scan, so skipping its hash saves time and disk reads.
7. **What is SHA-256?** — It is a cryptographic hash function that turns file bytes into a fixed-length digest. The program streams bytes in chunks and compares digests after the size filter.
8. **Can a matching name prove two files are duplicates?** — No. Different files can share a name, and identical contents can have different names. This application compares content hashes.
9. **What does reclaimable storage mean?** — For a group of `n` equal files of size `s`, it reports `(n - 1) × s`. It is potential space if extra copies were removed later; the application itself does not delete them.
10. **Why does the organizer show a preview?** — A preview lets the user inspect every source, category, and destination before any move. The operation starts only after the user confirms.
11. **How are filename collisions handled?** — The application checks for an existing name and selects a numbered name such as `report (1).pdf`. It uses exclusive destination creation so an existing destination is not intentionally replaced.
12. **What does revalidation mean?** — The organizer checks that a source still exists inside the selected root, has not changed since preview, and does not already live in the generated output folder before copying it.
13. **Why use classes?** — `FileScanner`, `DuplicateDetector`, `FileOrganizer`, `HistoryManager`, and `MainWindow` keep related data and behavior together. This separates file logic, persistence, reports, and interface code.
14. **How does JSON history work?** — Each scan becomes a dictionary of values and duplicate paths, appended to a JSON list. JSON is human-readable and suitable for this small local project.
15. **How does safe history writing help?** — It writes a complete new document to a temporary file, flushes it, and replaces the old file only when ready. A malformed existing history is preserved instead of being silently overwritten.
16. **Why use a background thread?** — Walking a large directory and hashing files can take time. The GUI starts this work on a worker thread and uses a queue so Tkinter widgets are changed only from the main thread.
17. **How is Matplotlib used?** — The report supplies category byte totals; the interface embeds a Matplotlib bar chart to make those totals easier to compare visually.
18. **What is a limitation of this project?** — Filesystems can change while a scan or copy is running, and interruptions such as power loss can happen. The program handles common errors and reports them, but no desktop utility can promise perfect protection against every race or hardware failure.

## Known limitations and future enhancements

- The chart is expressed in MiB; very small categories may appear close to zero.
- A full scan stores metadata for every file in memory, which may be expensive for exceptionally large folder trees.
- History is a local JSON file. It is intended for this mini project rather than concurrent multi-user access or very large histories.
- Windows GUI behavior should be verified on the target computer. The current development environment may not provide an interactive desktop display.
- Possible future work: filters and sorting, cancellation for very large scans, configurable category mappings, exportable reports, and a portable installer.
