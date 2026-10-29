import tempfile
import unittest
from pathlib import Path

from core.file_categories import classify_extension
from core.scanner import FileScanner


class FileScannerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1])
        self.root = Path(self.temp.name)
        self.scanner = FileScanner()

    def tearDown(self):
        self.temp.cleanup()

    def test_scans_files_recursively_and_collects_metadata(self):
        nested = self.root / "folder"
        nested.mkdir()
        file = nested / "notes.TXT"
        file.write_text("hello", encoding="utf-8")
        result = self.scanner.scan(self.root)
        self.assertEqual(len(result.files), 1)
        info = result.files[0]
        self.assertEqual(info.name, "notes.TXT")
        self.assertEqual(info.extension, ".txt")
        self.assertEqual(info.size, 5)
        self.assertEqual(info.category, "Documents")
        self.assertEqual(Path(info.path), file.absolute())
        self.assertTrue(info.modified_at)

    def test_missing_and_file_paths_raise_clear_errors(self):
        with self.assertRaises(FileNotFoundError):
            self.scanner.scan(self.root / "missing")
        file = self.root / "single.txt"
        file.touch()
        with self.assertRaises(NotADirectoryError):
            self.scanner.scan(file)

    def test_scan_excludes_generated_organized_directory(self):
        (self.root / "visible.txt").write_text("a", encoding="utf-8")
        organized = self.root / "Organized" / "Documents"
        organized.mkdir(parents=True)
        (organized / "old.txt").write_text("b", encoding="utf-8")
        result = self.scanner.scan(self.root)
        self.assertEqual([item.name for item in result.files], ["visible.txt"])

    def test_extension_categories_include_unknown_and_no_extension(self):
        self.assertEqual(classify_extension(".PDF"), "Documents")
        self.assertEqual(classify_extension(".png"), "Images")
        self.assertEqual(classify_extension(".mp4"), "Videos")
        self.assertEqual(classify_extension(".mp3"), "Audio")
        self.assertEqual(classify_extension(".zip"), "Archives")
        self.assertEqual(classify_extension(".py"), "Code")
        self.assertEqual(classify_extension(".mystery"), "Others")
        self.assertEqual(classify_extension(None), "Others")


if __name__ == "__main__":
    unittest.main()
