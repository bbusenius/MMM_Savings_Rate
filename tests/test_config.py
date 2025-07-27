import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from mmm_savings_rate.savings_rate import SavingsRate, SRConfig


class TestSRConfig(unittest.TestCase):
    """
    Test the SRConfig class with TinyDB configuration.
    """

    def setUp(self):
        self.config = SRConfig(user_id=1)
        self.sr = SavingsRate(self.config)

    def tearDown(self):
        # Close database connections to prevent ResourceWarnings
        if hasattr(self, 'config'):
            self.config.close()

    def test_config_initialization(self):
        """
        Test that SRConfig initializes correctly with a user ID.
        """
        # Test passes if config initializes without errors
        self.assertIsNotNone(self.config)
        self.assertEqual(self.config.user_id, 1)

    def test_file_extension(self):
        val1 = self.sr.config.file_extension('test.txt')
        val2 = self.sr.config.file_extension('/this/is/just/a/test.csv')
        val3 = self.sr.config.file_extension('')

        self.assertEqual(val1, '.txt')
        self.assertEqual(val2, '.csv')
        self.assertEqual(val3, '')

    def test_goal_and_fi_number_when_non_numeric_value_is_provided(self):
        with mock.patch('builtins.print') as mock_print:
            # Create a temporary TinyDB config with bad values
            temp_dir = tempfile.mkdtemp()
            test_db_path = Path(temp_dir) / "test_bad_values.json"

            # Get absolute paths to CSV files
            project_root = Path(__file__).parent.parent
            income_csv_path = project_root / "csv" / "income-example.csv"
            savings_csv_path = project_root / "csv" / "savings-example.csv"

            bad_config = {
                "main_user_settings": {
                    "pay": str(income_csv_path),  # Use absolute path to test file
                    "pay_date": "Date",
                    "gross_income": "Gross Pay",
                    "employer_match": "Employer Match",
                    "taxes_and_fees": ["OASDI", "Medicare"],
                    "savings": str(savings_csv_path),  # Use absolute path to test file
                    "savings_date": "Date",
                    "savings_accounts": ["Scottrade", "Vanguard 403b", "Vanguard Roth"],
                    "notes": "Notes",
                    "show_average": True,
                    "war": "off",
                    "fred_url": "",
                    "fred_api_key": "",
                    "goal": "Not a number",  # Bad value
                    "fi_number": "Also not a number",  # Bad value
                    "total_balances": "",
                    "percent_fi_notes": "",
                },
                "users": [
                    {"_id": 1, "name": "TestUser", "config_ref": "main_user_settings"}
                ],
                "enemy_settings": [],
            }

            with open(test_db_path, 'w') as f:
                json.dump(bad_config, f, indent=2)

            try:
                config_bad = SRConfig(test=True, test_file=str(test_db_path), user_id=1)
                self.assertEqual(config_bad.goal, False)
                self.assertEqual(config_bad.fi_number, False)

                self.assertEqual(mock_print.call_count, 2)

                # Check that the correct error messages were printed
                self.assertEqual(
                    mock_print.call_args_list[0][0][0],
                    "The value for 'goal' should be numeric, e.g. 65.",
                )
                self.assertEqual(
                    mock_print.call_args_list[1][0][0],
                    "The value for 'fi_number' should be numeric, e.g. 65.",
                )
            finally:
                # Close SRConfig to prevent ResourceWarnings
                if config_bad is not None:
                    config_bad.close()

                # Clean up temporary files
                if temp_dir and os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)


class TestFREDConfig(unittest.TestCase):
    """Test FRED configuration loading and validation."""

    def setUp(self):
        """Set up test fixtures with TinyDB configs for FRED testing."""
        # Create config with FRED settings
        self.temp_dir = tempfile.mkdtemp()
        self.test_db_path = Path(self.temp_dir) / "test_fred.json"

        # Get absolute paths to CSV files
        project_root = Path(__file__).parent.parent
        income_csv_path = project_root / "csv" / "income-example.csv"
        savings_csv_path = project_root / "csv" / "savings-example.csv"

        fred_config = {
            "main_user_settings": {
                "pay": str(income_csv_path),
                "pay_date": "Date",
                "gross_income": "Gross Pay",
                "employer_match": "Employer Match",
                "taxes_and_fees": ["OASDI", "Medicare"],
                "savings": str(savings_csv_path),
                "savings_date": "Date",
                "savings_accounts": ["Scottrade", "Vanguard 403b", "Vanguard Roth"],
                "notes": "Notes",
                "show_average": True,
                "war": "off",
                "fred_url": "https://fred-test.com",
                "fred_api_key": "test-api-key",
                "goal": False,
                "fi_number": False,
                "total_balances": False,
                "percent_fi_notes": "",
            },
            "users": [
                {"_id": 1, "name": "TestUser", "config_ref": "main_user_settings"}
            ],
            "enemy_settings": [],
        }

        with open(self.test_db_path, 'w') as f:
            json.dump(fred_config, f, indent=2)

        # Create config with missing FRED settings
        self.test_db_path_no_fred = Path(self.temp_dir) / "test_no_fred.json"

        no_fred_config = {
            "main_user_settings": {
                "pay": str(income_csv_path),
                "pay_date": "Date",
                "gross_income": "Gross Pay",
                "employer_match": "Employer Match",
                "taxes_and_fees": ["OASDI", "Medicare"],
                "savings": str(savings_csv_path),
                "savings_date": "Date",
                "savings_accounts": ["Scottrade", "Vanguard 403b", "Vanguard Roth"],
                "notes": "Notes",
                "show_average": True,
                "war": "off",
                "fred_url": "",
                "fred_api_key": "",
                "goal": False,
                "fi_number": False,
                "total_balances": False,
                "percent_fi_notes": "",
            },
            "users": [
                {"_id": 1, "name": "TestUser", "config_ref": "main_user_settings"}
            ],
            "enemy_settings": [],
        }

        with open(self.test_db_path_no_fred, 'w') as f:
            json.dump(no_fred_config, f, indent=2)

        # Create SRConfig instances
        self.config = SRConfig(test=True, test_file=str(self.test_db_path), user_id=1)
        self.sr = SavingsRate(self.config)
        self.config_missing = SRConfig(
            test=True, test_file=str(self.test_db_path_no_fred), user_id=1
        )
        self.sr_no_fred = SavingsRate(self.config_missing)

    def tearDown(self):
        """Clean up test fixtures."""
        # Close database connections to prevent ResourceWarnings
        if hasattr(self, 'config'):
            self.config.close()
        if hasattr(self, 'config_missing'):
            self.config_missing.close()

        # Clean up temporary files
        import os
        import shutil

        if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_load_fred_config(self):
        """Test loading FRED configuration from TinyDB."""
        has_fred = self.sr.config.has_fred()
        self.assertEqual(self.sr.config.fred_url, 'https://fred-test.com')
        self.assertEqual(self.sr.config.fred_api_key, 'test-api-key')
        self.assertEqual(has_fred, True)

    def test_load_fred_with_no_fred_settings(self):
        """Test handling of missing FRED settings."""
        has_fred = self.sr_no_fred.config.has_fred()
        self.assertEqual(self.sr_no_fred.config.fred_url, '')
        self.assertEqual(self.sr_no_fred.config.fred_api_key, '')
        self.assertEqual(has_fred, False)


class TestConfigurationFeatures(unittest.TestCase):
    """Test various configuration features and their behavior."""

    def setUp(self):
        """Set up test fixtures for configuration feature testing."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_db_path = Path(self.temp_dir) / "test_config_features.json"

        # Get absolute paths to CSV files
        project_root = Path(__file__).parent.parent
        income_csv_path = project_root / "csv" / "income-example.csv"
        savings_csv_path = project_root / "csv" / "savings-example.csv"

        # Base config with all features
        self.base_config = {
            "main_user_settings": {
                "pay": str(income_csv_path),
                "pay_date": "Date",
                "gross_income": "Gross Pay",
                "employer_match": "Employer Match",
                "taxes_and_fees": ["OASDI", "Medicare"],
                "savings": str(savings_csv_path),
                "savings_date": "Date",
                "savings_accounts": ["Scottrade", "Vanguard 403b", "Vanguard Roth"],
                "notes": "Test notes content",
                "show_average": True,
                "war": "off",
                "fred_url": "",
                "fred_api_key": "",
                "goal": 1000000,
                "fi_number": 25,
                "total_balances": True,
                "percent_fi_notes": "FI calculation notes",
            },
            "users": [
                {"_id": 1, "name": "TestUser", "config_ref": "main_user_settings"}
            ],
            "enemy_settings": [],
        }

    def tearDown(self):
        """Clean up test fixtures."""
        # Close any config instances
        if hasattr(self, 'config'):
            self.config.close()

        if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_load_notes_config(self):
        """Test that notes configuration loads correctly."""
        with open(self.test_db_path, 'w') as f:
            json.dump(self.base_config, f, indent=2)

        config = SRConfig(test=True, test_file=str(self.test_db_path), user_id=1)
        try:
            self.assertEqual(config.notes, "Test notes content")
        finally:
            config.close()

    def test_load_notes_config_default(self):
        """Test that notes default to empty string when missing."""
        config_no_notes = self.base_config.copy()
        del config_no_notes["main_user_settings"]["notes"]

        with open(self.test_db_path, 'w') as f:
            json.dump(config_no_notes, f, indent=2)

        config = SRConfig(test=True, test_file=str(self.test_db_path), user_id=1)
        try:
            self.assertEqual(config.notes, "")
        finally:
            config.close()

    def test_load_show_average_config(self):
        """Test that show_average configuration loads correctly."""
        # Test True value
        with open(self.test_db_path, 'w') as f:
            json.dump(self.base_config, f, indent=2)

        config = SRConfig(test=True, test_file=str(self.test_db_path), user_id=1)
        try:
            self.assertEqual(config.show_average, True)
        finally:
            config.close()

        # Test False value
        config_false = self.base_config.copy()
        config_false["main_user_settings"]["show_average"] = False

        with open(self.test_db_path, 'w') as f:
            json.dump(config_false, f, indent=2)

        config = SRConfig(test=True, test_file=str(self.test_db_path), user_id=1)
        try:
            self.assertEqual(config.show_average, False)
        finally:
            config.close()

    def test_load_show_average_config_default(self):
        """Test that show_average defaults to True when missing."""
        config_no_show_avg = self.base_config.copy()
        del config_no_show_avg["main_user_settings"]["show_average"]

        with open(self.test_db_path, 'w') as f:
            json.dump(config_no_show_avg, f, indent=2)

        config = SRConfig(test=True, test_file=str(self.test_db_path), user_id=1)
        try:
            self.assertEqual(config.show_average, True)
        finally:
            config.close()

    def test_load_total_balances_config(self):
        """Test that total_balances configuration loads correctly."""
        with open(self.test_db_path, 'w') as f:
            json.dump(self.base_config, f, indent=2)

        config = SRConfig(test=True, test_file=str(self.test_db_path), user_id=1)
        try:
            self.assertEqual(config.total_balances, True)
        finally:
            config.close()

    def test_load_total_balances_config_default(self):
        """Test that total_balances defaults to False when missing."""
        config_no_total_balances = self.base_config.copy()
        del config_no_total_balances["main_user_settings"]["total_balances"]

        with open(self.test_db_path, 'w') as f:
            json.dump(config_no_total_balances, f, indent=2)

        config = SRConfig(test=True, test_file=str(self.test_db_path), user_id=1)
        try:
            self.assertEqual(config.total_balances, False)
        finally:
            config.close()

    def test_load_percent_fi_notes_config(self):
        """Test that percent_fi_notes configuration loads correctly."""
        with open(self.test_db_path, 'w') as f:
            json.dump(self.base_config, f, indent=2)

        config = SRConfig(test=True, test_file=str(self.test_db_path), user_id=1)
        try:
            self.assertEqual(config.percent_fi_notes, "FI calculation notes")
        finally:
            config.close()

    def test_load_percent_fi_notes_config_default(self):
        """Test that percent_fi_notes defaults to empty string when missing."""
        config_no_percent_fi_notes = self.base_config.copy()
        del config_no_percent_fi_notes["main_user_settings"]["percent_fi_notes"]

        with open(self.test_db_path, 'w') as f:
            json.dump(config_no_percent_fi_notes, f, indent=2)

        config = SRConfig(test=True, test_file=str(self.test_db_path), user_id=1)
        try:
            self.assertEqual(config.percent_fi_notes, "")
        finally:
            config.close()

    def test_numeric_goal_config_various_formats(self):
        """Test that goal loads correctly in various numeric formats."""
        test_cases = [
            (1000000, 1000000),  # int
            (1000000.0, 1000000.0),  # float
            ("1000000", 1000000),  # string int
            ("1000000.5", 1000000.5),  # string float
            (None, False),  # missing
            ("invalid", False),  # non-numeric string
        ]

        for test_value, expected in test_cases:
            with self.subTest(test_value=test_value, expected=expected):
                config_test = self.base_config.copy()
                if test_value is None:
                    del config_test["main_user_settings"]["goal"]
                else:
                    config_test["main_user_settings"]["goal"] = test_value

                with open(self.test_db_path, 'w') as f:
                    json.dump(config_test, f, indent=2)

                config = SRConfig(
                    test=True, test_file=str(self.test_db_path), user_id=1
                )
                try:
                    self.assertEqual(config.goal, expected)
                finally:
                    config.close()

    def test_numeric_fi_number_config_various_formats(self):
        """Test that fi_number loads correctly in various numeric formats."""
        test_cases = [
            (25, 25),  # int
            (25.5, 25.5),  # float
            ("25", 25),  # string int
            ("25.5", 25.5),  # string float
            (None, False),  # missing
            ("invalid", False),  # non-numeric string
        ]

        for test_value, expected in test_cases:
            with self.subTest(test_value=test_value, expected=expected):
                config_test = self.base_config.copy()
                if test_value is None:
                    del config_test["main_user_settings"]["fi_number"]
                else:
                    config_test["main_user_settings"]["fi_number"] = test_value

                with open(self.test_db_path, 'w') as f:
                    json.dump(config_test, f, indent=2)

                config = SRConfig(
                    test=True, test_file=str(self.test_db_path), user_id=1
                )
                try:
                    self.assertEqual(config.fi_number, expected)
                finally:
                    config.close()
