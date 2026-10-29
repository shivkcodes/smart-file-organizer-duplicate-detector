import json
import tempfile
import unittest
from pathlib import Path

from storage.history_manager import HistoryFormatError, HistoryManager


class HistoryManagerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1])
        self.path = Path(self.temp.name) / "data" / "scan_history.json"
        self.manager = HistoryManager(self.path)

    def tearDown(self):
        self.temp.cleanup()

    def test_missing_file_loads_as_empty_and_save_creates_it(self):
        self.assertEqual(self.manager.load(), [])
        self.manager.save({"root_path": "/example", "total_file_count": 2})
        self.assertEqual(self.manager.load(), [{"root_path": "/example", "total_file_count": 2}])

    def test_save_appends_and_load_reads_records(self):
        self.manager.save({"id": 1})
        self.manager.save({"id": 2})
        self.assertEqual(self.manager.load(), [{"id": 1}, {"id": 2}])

    def test_malformed_json_is_reported_and_preserved_on_save(self):
        self.path.parent.mkdir(parents=True)
        original = "{broken json"
        self.path.write_text(original, encoding="utf-8")
        records, warnings = self.manager.load_with_warnings()
        self.assertEqual(records, [])
        self.assertTrue(warnings)
        with self.assertRaises(HistoryFormatError):
            self.manager.save({"new": True})
        self.assertEqual(self.path.read_text(encoding="utf-8"), original)

    def test_invalid_history_root_is_reported(self):
        self.path.parent.mkdir(parents=True)
        self.path.write_text(json.dumps({"not": "a list"}), encoding="utf-8")
        records, warnings = self.manager.load_with_warnings()
        self.assertEqual(records, [])
        self.assertIn("JSON list", warnings[0])

    def test_write_failure_does_not_truncate_existing_path(self):
        self.path.parent.mkdir(parents=True)
        self.path.mkdir()
        with self.assertRaises(HistoryFormatError):
            self.manager.save({"x": 1})
        self.assertTrue(self.path.is_dir())


if __name__ == "__main__":
    unittest.main()
