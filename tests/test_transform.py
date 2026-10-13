import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src import transform


class WeatherValidationTests(unittest.TestCase):
    def record(self, **values):
        return {
            "city": "Pune",
            "temperature": 26.2,
            "humidity": 78,
            "wind_speed": 12.5,
            "recorded_at": "2026-10-13T12:00",
            **values,
        }

    def test_rejects_non_finite_measurements(self):
        for field in ("temperature", "humidity", "wind_speed"):
            for value in (float("nan"), float("inf"), float("-inf"), "inf", "-inf", "NaN"):
                with self.subTest(field=field, value=value):
                    with self.assertRaisesRegex(ValueError, field):
                        transform.validate_weather_record(self.record(**{field: value}))

    def test_accepts_finite_numbers_and_numeric_strings(self):
        for humidity in (0, 100, "0", "100"):
            with self.subTest(humidity=humidity):
                transform.validate_weather_record(
                    self.record(temperature="-12.5", humidity=humidity, wind_speed="0")
                )

    def test_retains_humidity_range_validation(self):
        for humidity in (-1, 101):
            with self.subTest(humidity=humidity):
                with self.assertRaisesRegex(ValueError, "humidity"):
                    transform.validate_weather_record(self.record(humidity=humidity))

    def test_invalid_measurement_does_not_write_processed_csv(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw = root / "weather.json"
            raw.write_text(json.dumps({"current": {
                "temperature_2m": "Infinity",
                "relative_humidity_2m": 78,
                "wind_speed_10m": 12.5,
                "time": "2026-10-13T12:00",
            }}), encoding="utf-8")
            processed = root / "processed"
            with patch.object(transform, "PROCESSED_DATA_DIR", processed):
                with self.assertRaisesRegex(ValueError, "temperature"):
                    transform.transform_weather(raw)
            self.assertFalse(processed.exists())


if __name__ == "__main__":
    unittest.main()
