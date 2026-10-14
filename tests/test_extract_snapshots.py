import json
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from src import extract


class RawSnapshotTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name) / "raw"
        directory_patch = patch.object(extract, "RAW_DATA_DIR", self.directory)
        directory_patch.start()
        self.addCleanup(directory_patch.stop)
        clock_patch = patch.object(extract, "datetime")
        clock = clock_patch.start()
        clock.now.return_value = datetime(2026, 10, 14, 12, 0, 0)
        self.addCleanup(clock_patch.stop)

    def test_two_saves_in_same_second_preserve_both_payloads(self):
        first = extract.save_raw_json({"reading": 1})
        second = extract.save_raw_json({"reading": 2})
        self.assertNotEqual(first, second)
        self.assertEqual(json.loads(first.read_text(encoding="utf-8")), {"reading": 1})
        self.assertEqual(json.loads(second.read_text(encoding="utf-8")), {"reading": 2})
        self.assertEqual(len(list(self.directory.glob("weather_*.json"))), 2)

    def test_existing_snapshot_is_not_overwritten(self):
        self.directory.mkdir()
        existing = self.directory / "weather_20261014_120000.json"
        existing.write_text('{"original": true}', encoding="utf-8")
        saved = extract.save_raw_json({"new": True})
        self.assertNotEqual(existing, saved)
        self.assertEqual(existing.read_text(encoding="utf-8"), '{"original": true}')
        self.assertEqual(json.loads(saved.read_text(encoding="utf-8")), {"new": True})

    def test_concurrent_saves_preserve_every_payload(self):
        payloads = [{"reading": number} for number in range(12)]
        with ThreadPoolExecutor(max_workers=4) as executor:
            paths = list(executor.map(extract.save_raw_json, payloads))
        self.assertEqual(len(set(paths)), len(payloads))
        for path, expected in zip(paths, payloads):
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), expected)


if __name__ == "__main__":
    unittest.main()
