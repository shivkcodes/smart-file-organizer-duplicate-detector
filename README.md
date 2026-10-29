# Smart File Organizer & Duplicate Detector

A Python-based desktop application that simplifies file management by automatically categorizing files, detecting duplicate content, and visualizing storage usage through an interactive graphical interface.

## Overview

Managing files manually can become time-consuming when folders contain hundreds or thousands of documents, images, videos, and other files. The **Smart File Organizer & Duplicate Detector** provides a practical solution by scanning selected directories, classifying files by extension, identifying duplicates using SHA-256 hashing, and organizing files into category-wise folders.

The application includes an organization preview so users can review proposed file movements before confirming them. It also provides storage analytics and JSON-based scan history to help users understand their file distribution and potential storage savings.

## Features

- **Recursive File Scanning:** Scan selected folders and collect file information.
- **Automatic File Categorization:** Group files into Documents, Images, Videos, Audio, Archives, Code, and Others.
- **Duplicate Detection:** Identify files with matching content using SHA-256 hashing, with file size used as an initial filter.
- **Organization Preview:** Review proposed file movements before making changes.
- **Safe File Organization:** Move files into category-wise folders while avoiding accidental overwriting of existing files.
- **Storage Analytics:** View total file counts, category-wise storage usage, and potential storage occupied by duplicates.
- **Scan History:** Store and retrieve scan records using JSON.
- **Graphical User Interface:** Use a desktop interface built with Tkinter and ttk.
- **Data Visualization:** Display storage statistics and charts using Matplotlib.
- **Automated Testing:** Test core functionality, including scanning, organization, duplicate detection, history, and reports.

## Technologies Used

| Technology | Purpose |
|---|---|
| Python | Core programming language |
| Tkinter and ttk | Desktop graphical user interface |
| `pathlib` | File and directory path management |
| `shutil` | File operations and movement |
| `hashlib` | SHA-256 content hashing |
| JSON | Persistent scan history |
| Matplotlib | Storage analytics and charts |
| `unittest` | Automated testing |

## Project Structure

```text
Smart-File-Organizer/
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

## Installation

### Prerequisites

- Windows 10 or Windows 11
- Python 3.12 or 3.13 recommended
- Git
- Visual Studio Code or another Python IDE

### 1. Clone the repository

Replace `YOUR_USERNAME` with your GitHub username.

```bash
git clone https://github.com/YOUR_USERNAME/smart-file-organizer-duplicate-detector.git
cd smart-file-organizer-duplicate-detector
```

### 2. Create a virtual environment

```bash
python -m venv .venv
```

### 3. Activate the virtual environment

On Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

If PowerShell activation is unavailable, run the application directly through the virtual environment's Python executable.

### 4. Install dependencies

```bash
python -m pip install -r requirements.txt
```

### 5. Run the application

```bash
python main.py
```

## How to Use

1. Launch the application.
2. Select the folder you want to scan.
3. Start the scan to collect file information.
4. Review file categories and duplicate detection results.
5. Open the analytics view to inspect storage statistics.
6. Preview the proposed organization before confirming it.
7. Confirm the operation to move files into the appropriate category folders.
8. Review saved scan records in the history section.

## How Duplicate Detection Works

The application uses a two-stage approach:

1. **File-size filtering:** Files with different sizes are excluded from direct duplicate comparisons.
2. **SHA-256 hashing:** Candidate files are read in chunks and hashed. Matching hashes indicate matching file content, subject to the security properties of the hash algorithm.

This approach reduces unnecessary hashing and avoids loading entire large files into memory at once.

## File Organization

Files are organized into category-specific subfolders inside an `Organized` directory within the selected folder.

Example:

```text
SelectedFolder/
├── report.pdf
├── holiday.jpg
├── recording.mp3
└── Organized/
    ├── Documents/
    ├── Images/
    ├── Audio/
    └── Others/
```

The application provides a preview before organization and avoids overwriting existing files. Review the proposed destinations before confirming any file movement.

**Important:** Always maintain backups of important data. Review the selected folder and preview before confirming organization.

## Testing

The project includes automated tests for its major components.

Run the test suite from the project root:

```bash
python -m unittest discover -s tests -v
```

The tests cover file scanning, organization, duplicate detection, scan history, and analytics calculations.

## Limitations

- File categorization is primarily based on file extensions.
- Duplicate detection identifies matching content; it does not determine whether different files are semantically similar.
- Performance depends on directory size, file sizes, disk speed, and available system resources.
- Files may be inaccessible because of permissions or operating-system restrictions.
- The application is designed as a local desktop utility rather than a cloud-based file management service.

## Future Improvements

- Support configurable categories and custom organization rules.
- Add exportable CSV and PDF analytics reports.
- Improve recovery options for interrupted file operations.
- Enhance performance for very large directories.
- Add more advanced search, filtering, and reporting features.
- Improve accessibility and interface customization.

## Learning Outcomes

This project demonstrates practical knowledge of Python programming, modular architecture, file handling, exception handling, cryptographic hashing, JSON persistence, graphical user interface development, data visualization, and automated testing.

## Contributing

Contributions, suggestions, and bug reports are welcome. To propose a change, fork the repository, create a feature branch, make your changes, and submit a pull request.

## License

No license has been specified yet. Add an appropriate open-source license before permitting others to reuse, modify, or distribute this project.

## Author

**Your Name**

GitHub: https://github.com/shivkcodes

---

If you find this project useful, consider giving the repository a star!