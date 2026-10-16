import os
import unittest
from unittest.mock import patch

from src import load


class DatabaseConfigTests(unittest.TestCase):
    def config(self, password):
        environment = {
            "DB_HOST": " localhost ",
            "DB_PORT": " 5432 ",
            "DB_NAME": " weather_db ",
            "DB_USER": " postgres ",
        }
        if password is not None:
            environment["DB_PASSWORD"] = password
        with patch.dict(os.environ, environment, clear=True):
            with patch.object(load, "load_dotenv"):
                return load.get_database_config()

    def test_password_is_preserved_exactly(self):
        for password in (" leading", "trailing ", " both ", " ", "\ttest\t"):
            with self.subTest(password=repr(password)):
                self.assertEqual(self.config(password)["password"], password)

    def test_missing_and_empty_passwords_are_rejected(self):
        for password in (None, ""):
            with self.subTest(password=password):
                with self.assertRaisesRegex(ValueError, "DB_PASSWORD"):
                    self.config(password)

    def test_other_settings_still_trim_surrounding_whitespace(self):
        config = self.config("test-password")
        self.assertEqual(config, {
            "host": "localhost", "port": "5432", "dbname": "weather_db",
            "user": "postgres", "password": "test-password",
        })

    def test_connection_receives_unmodified_password(self):
        config = self.config(" test-password ")
        with patch.object(load.psycopg2, "connect") as connect:
            load.connect_to_database(config)
        self.assertEqual(connect.call_args.kwargs["password"], " test-password ")


if __name__ == "__main__":
    unittest.main()
