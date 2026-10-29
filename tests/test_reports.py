import unittest
from core.duplicate_detector import DuplicateGroup
from core.scanner import FileInfo
from analytics.reports import build_report, format_bytes


class ReportTests(unittest.TestCase):
    def test_summary_calculates_totals_from_scan_results(self):
        files = [
            FileInfo("a.txt", ".txt", 10, "/a", "now", "Documents", 1),
            FileInfo("b.png", ".png", 20, "/b", "now", "Images", 2),
        ]
        groups = [DuplicateGroup("abc", 10, ("/a", "/copy"))]
        report = build_report(files, groups)
        self.assertEqual(report["total_file_count"], 2)
        self.assertEqual(report["total_size"], 30)
        self.assertEqual(report["category_counts"], {"Documents": 1, "Images": 1})
        self.assertEqual(report["duplicate_group_count"], 1)
        self.assertEqual(report["duplicate_file_count"], 2)
        self.assertEqual(report["potential_reclaimable_bytes"], 10)

    def test_empty_report_and_size_format(self):
        self.assertEqual(build_report([], []) ["total_file_count"], 0)
        self.assertEqual(format_bytes(1024), "1.00 KiB")


if __name__ == "__main__":
    unittest.main()
