import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from core.organizer import FileOrganizer
from core.scanner import FileScanner


class FileOrganizerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1])
        self.root = Path(self.temp.name)
        self.organizer = FileOrganizer()

    def tearDown(self):
        self.temp.cleanup()

    def scanned_files(self):
        return FileScanner().scan(self.root).files

    def test_preview_lists_paths_without_moving_or_creating_destination(self):
        source = self.root / "report.pdf"
        source.write_text("report", encoding="utf-8")
        preview = self.organizer.create_preview(self.root, self.scanned_files())
        self.assertEqual(len(preview), 1)
        self.assertEqual(preview[0].status, "Ready")
        self.assertEqual(Path(preview[0].destination), self.root / "Organized" / "Documents" / "report.pdf")
        self.assertTrue(source.exists())
        self.assertFalse((self.root / "Organized").exists())

    def test_cancelled_preview_leaves_files_unchanged(self):
        source = self.root / "image.png"
        source.write_bytes(b"pixels")
        preview = self.organizer.create_preview(self.root, self.scanned_files())
        # A cancelled preview is never passed to execute; preview creation itself is read-only.
        self.assertTrue(source.exists())
        self.assertEqual(preview[0].status, "Ready")
        self.assertFalse((self.root / "Organized").exists())

    def test_confirmed_operation_moves_file_under_category(self):
        source = self.root / "source.py"
        source.write_text("print('ok')", encoding="utf-8")
        preview = self.organizer.create_preview(self.root, self.scanned_files())
        result = self.organizer.execute(self.root, preview)
        destination = self.root / "Organized" / "Code" / "source.py"
        self.assertEqual(result[0].status, "Moved")
        self.assertFalse(source.exists())
        self.assertEqual(destination.read_text(encoding="utf-8"), "print('ok')")

    def test_existing_destination_gets_unique_name_without_overwrite(self):
        source = self.root / "report.txt"
        source.write_text("new", encoding="utf-8")
        destination_dir = self.root / "Organized" / "Documents"
        destination_dir.mkdir(parents=True)
        (destination_dir / "report.txt").write_text("existing", encoding="utf-8")
        preview = self.organizer.create_preview(self.root, self.scanned_files())
        result = self.organizer.execute(self.root, preview)
        self.assertEqual(result[0].status, "Moved")
        self.assertEqual((destination_dir / "report.txt").read_text(encoding="utf-8"), "existing")
        self.assertEqual((destination_dir / "report (1).txt").read_text(encoding="utf-8"), "new")

    def test_stale_source_is_skipped_after_preview(self):
        source = self.root / "data.csv"
        source.write_text("old", encoding="utf-8")
        preview = self.organizer.create_preview(self.root, self.scanned_files())
        source.write_text("changed content", encoding="utf-8")
        result = self.organizer.execute(self.root, preview)
        self.assertTrue(result[0].status.startswith("Failed: source changed"))
        self.assertTrue(source.exists())

    def test_outside_source_is_skipped(self):
        source = self.root / "safe.txt"
        source.write_text("x", encoding="utf-8")
        file_info = self.scanned_files()[0]
        outside = replace(file_info, path=str(self.root.parent / "outside.txt"))
        preview = self.organizer.create_preview(self.root, [outside])
        self.assertTrue(preview[0].status.startswith("Skipped: source is outside"))

    def test_unknown_category_is_rejected_before_creating_destination(self):
        source = self.root / "safe.txt"
        source.write_text("x", encoding="utf-8")
        file_info = replace(self.scanned_files()[0], category="../outside")
        preview = self.organizer.create_preview(self.root, [file_info])
        self.assertEqual(preview[0].status, "Skipped: unknown file category")
        self.assertFalse((self.root / "Organized").exists())

    def test_already_organized_files_are_not_scanned_or_planned(self):
        organized = self.root / "Organized" / "Images"
        organized.mkdir(parents=True)
        (organized / "already.png").write_bytes(b"x")
        self.assertEqual(self.scanned_files(), [])
        preview = self.organizer.create_preview(self.root, [])
        self.assertEqual(preview, [])


if __name__ == "__main__":
    unittest.main()
