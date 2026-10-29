import tempfile
import unittest
from pathlib import Path

from core.duplicate_detector import DuplicateDetector
from core.scanner import FileScanner


class DuplicateDetectorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1])
        self.root = Path(self.temp.name)
        self.scanner = FileScanner()

    def tearDown(self):
        self.temp.cleanup()

    def test_identical_content_is_duplicate_even_with_different_names(self):
        (self.root / "one.dat").write_bytes(b"same payload")
        (self.root / "two.bin").write_bytes(b"same payload")
        result = DuplicateDetector().find_duplicates(self.scanner.scan(self.root).files)
        self.assertEqual(len(result.groups), 1)
        self.assertEqual(result.groups[0].file_count, 2)
        self.assertEqual(result.groups[0].size, len(b"same payload"))
        self.assertEqual(result.groups[0].reclaimable_bytes, len(b"same payload"))

    def test_same_size_different_content_is_not_duplicate(self):
        (self.root / "one.txt").write_bytes(b"abcd")
        (self.root / "two.txt").write_bytes(b"wxyz")
        result = DuplicateDetector().find_duplicates(self.scanner.scan(self.root).files)
        self.assertEqual(result.groups, [])

    def test_only_one_copy_beyond_retained_copy_is_reclaimable(self):
        for name in ("a", "b", "c"):
            (self.root / name).write_bytes(b"1234567")
        result = DuplicateDetector().find_duplicates(self.scanner.scan(self.root).files)
        self.assertEqual(len(result.groups), 1)
        self.assertEqual(result.groups[0].file_count, 3)
        self.assertEqual(result.groups[0].reclaimable_bytes, 14)

    def test_changed_or_missing_file_is_reported_and_skipped(self):
        file = self.root / "one.txt"
        file.write_bytes(b"abcd")
        (self.root / "two.txt").write_bytes(b"abcd")
        scan = self.scanner.scan(self.root)
        file.write_bytes(b"changed")
        result = DuplicateDetector().find_duplicates(scan.files)
        self.assertEqual(result.groups, [])
        self.assertTrue(any("Could not hash" in warning for warning in result.warnings))


if __name__ == "__main__":
    unittest.main()
