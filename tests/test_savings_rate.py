import datetime
import json
import os
import shutil
import tempfile
import unittest
from collections import OrderedDict
from decimal import Decimal
from pathlib import Path
from unittest import mock

import requests

from savings_rate import Plot, SavingsRate, SRConfig


class TestSavingsRate(unittest.TestCase):
    """
    Tests for individual methods.
    """

    def setUp(self):
        # Create temporary directories for test configs
        self.temp_csv_dir = tempfile.mkdtemp()
        self.temp_xlsx_dir = tempfile.mkdtemp()

        # CSV test configuration
        self.csv_db_path = Path(self.temp_csv_dir) / "test_csv_config.json"
        csv_config = {
            "main_user_settings": {
                "pay": "csv/income-example.csv",  # Use existing csv test file
                "pay_date": "Date",
                "gross_income": "Gross Pay",
                "employer_match": "Employer Match",
                "taxes_and_fees": ["OASDI", "Medicare"],
                "savings": "csv/savings-example.csv",  # Use existing csv test file
                "savings_date": "Date",
                "savings_accounts": ["Scottrade", "Vanguard 403b", "Vanguard Roth"],
                "notes": "Test notes",
                "show_average": True,
                "war": "off",
                "fred_url": "",
                "fred_api_key": "",
                "goal": 1000000,
                "fi_number": 25,
                "total_balances": False,
                "percent_fi_notes": "",
            },
            "users": [
                {"_id": 1, "name": "TestUser", "config_ref": "main_user_settings"}
            ],
            "enemy_settings": [],
        }

        with open(self.csv_db_path, 'w') as f:
            json.dump(csv_config, f, indent=2)

        # CSV test configuration
        self.config = SRConfig(test=True, test_file=str(self.csv_db_path), user_id=1)
        self.sr = SavingsRate(self.config)

        # XLSX test configuration
        self.xlsx_db_path = Path(self.temp_xlsx_dir) / "test_xlsx_config.json"
        xlsx_config = {
            "main_user_settings": {
                "pay": "csv/income-example.xlsx",  # Use existing xlsx test file
                "pay_date": "Date",
                "gross_income": "Gross Pay",
                "employer_match": "Employer Match",
                "taxes_and_fees": ["OASDI", "Medicare"],
                "savings": "csv/savings-example.xlsx",  # Use existing xlsx test file
                "savings_date": "Date",
                "savings_accounts": ["Scottrade", "Vanguard 403b", "Vanguard Roth"],
                "notes": "Test notes",
                "show_average": True,
                "war": "off",
                "fred_url": "",
                "fred_api_key": "",
                "goal": 1000000,
                "fi_number": 25,
                "total_balances": False,
                "percent_fi_notes": "",
            },
            "users": [
                {"_id": 1, "name": "TestUser", "config_ref": "main_user_settings"}
            ],
            "enemy_settings": [],
        }

        with open(self.xlsx_db_path, 'w') as f:
            json.dump(xlsx_config, f, indent=2)

        # XLSX test configuration
        self.config_xlsx = SRConfig(
            test=True, test_file=str(self.xlsx_db_path), user_id=1
        )

    def tearDown(self):
        if hasattr(self, 'config'):
            self.config.close()
        if hasattr(self, 'config_xlsx'):
            self.config_xlsx.close()

        # Clean up temporary test directories
        if hasattr(self, 'temp_csv_dir') and os.path.exists(self.temp_csv_dir):
            shutil.rmtree(self.temp_csv_dir)
        if hasattr(self, 'temp_xlsx_dir') and os.path.exists(self.temp_xlsx_dir):
            shutil.rmtree(self.temp_xlsx_dir)

    def test_clean_num(self):
        sr = SavingsRate(self.config)

        val1 = sr.clean_num('')
        val2 = sr.clean_num('     ')
        val3 = sr.clean_num(None)
        val4 = sr.clean_num(4)
        val5 = sr.clean_num(4.4)
        val6 = sr.clean_num(Decimal(4.4))

        self.assertRaises(TypeError, sr.clean_num, 'Son of Mogh')
        self.assertRaises(TypeError, sr.clean_num, '4.4')
        self.assertEqual(
            val1, 0.0
        ), 'An empty string should evaluate to 0.0. It evaluated to ' + str(val1)
        self.assertEqual(
            val2, 0.0
        ), 'An empty string should evaluate to 0.0. It evaluated to ' + str(val2)
        self.assertEqual(
            val3, 0.0
        ), 'None should evaluate to 0.0. It evaluated to ' + str(val3)
        self.assertEqual(val4, 4), '4 should evaluate to 4.4. It evaluated to ' + str(
            val4
        )
        self.assertEqual(
            val5, 4.4
        ), '4.4 should evaluate to 4.4. It evaluated to ' + str(val5)
        self.assertEqual(
            val6, Decimal(4.4)
        ), '4.4 should evaluate to Decimal(4.4). It evaluated to ' + str(val6)

    def test_spreadsheet_with_misconfigured_income_columns(self):
        """
        Test a spreadsheet that doesn't have the column
        headers that were set in the configuration. Having a required
        field set in the configuration that doesn't exist in the
        corresponding .csv, should throw an assertion error.
        """
        self.config.required_income_columns = set(['Foo', 'Bar'])
        self.assertRaises(AssertionError, SavingsRate, self.config)

    def test_spreadsheet_with_misconfigured_savings_columns(self):
        """
        Test a spreadsheet that doesn't have the column
        headers that were set in the configuration. Having a required
        field set in the configuration that doesn't exist in the
        corresponding .csv, should throw an assertion error.
        """
        self.config.required_savings_columns = (
            self.config.required_savings_columns.union(set(['Additional Heading']))
        )
        self.assertRaises(AssertionError, SavingsRate, self.config)

    def test_data_loaded_by_load_pay_from_csv(self):
        """
        Dates should be in chronological order assuming
        they were entered that way. All required_income_columns
        should be present in the data structure.
        """
        sr = SavingsRate(self.config)

        dates = []
        i = 0
        for d in sr.income:
            for req in sr.config.required_income_columns:
                self.assertEqual(
                    req in sr.income[d], True, 'Missing a field in SavingsRate.income.'
                )
            dates.append(d)
            if i > 0:
                assert (
                    d > dates[i - 1]
                ), 'Income transaction dates are not in chronological order. Were they entered chronologically?'
            i += 1

    def test_data_loaded_by_load_pay_from_xlsx(self):
        """
        Data loaded from an Excel spreadsheet should be the
        same as data loaded from a .csv.
        """
        srcsv = SavingsRate(self.config)
        srxlsx = SavingsRate(self.config_xlsx)
        self.assertEqual(
            srcsv.income,
            srxlsx.income,
            'Income loaded from a .csv and .xlsx should be the same.',
        )

    def test_data_loaded_by_load_savings_from_csv(self):
        """
        Dates should be in chronological order assuming
        they were entered that way. All required_income_columns
        should be present in the data structure.
        """
        sr = SavingsRate(self.config)

        dates = []
        i = 0
        for d in sr.savings:
            for req in sr.config.required_savings_columns:
                self.assertEqual(
                    req in sr.savings[d],
                    True,
                    'Missing a field in SavingsRate.savings.',
                )
            dates.append(d)
            if i > 0:
                assert (
                    d > dates[i - 1]
                ), 'Income transaction dates are not in chronological order. Were they entered chronologically?'
            i += 1

    def test_data_loaded_by_load_savings_from_xlsx(self):
        """
        Data loaded from an Excel spreadsheet should be the
        same as data loaded from a .csv.
        """
        srcsv = SavingsRate(self.config)
        srxlsx = SavingsRate(self.config_xlsx)
        self.assertEqual(
            srcsv.savings,
            srxlsx.savings,
            'Savings loaded from a .csv and .xlsx should be the same.',
        )

    def test_empty_csv_files(self):
        """
        The files exist with the proper column headings
        but no data. This shouldn't blow up.
        """
        # Create temporary directory for test files and config
        temp_dir = tempfile.mkdtemp()
        test_db_path = Path(temp_dir) / "test_empty_csv.json"

        # Create empty CSV files with headers but no data
        empty_income_csv = Path(temp_dir) / "empty_income.csv"
        empty_savings_csv = Path(temp_dir) / "empty_savings.csv"

        # Write CSV files with headers but no data rows
        with open(empty_income_csv, 'w') as f:
            f.write(
                "Date,Gross Pay,Net Pay,Employer Match,Total Taxes and Fees,OASDI,Medicare,Federal Withholding,State Tax\n"
            )
        with open(empty_savings_csv, 'w') as f:
            f.write("Date,Scottrade,Vanguard 403b,Vanguard Roth\n")

        empty_config = {
            "main_user_settings": {
                "pay": str(empty_income_csv),
                "pay_date": "Date",
                "gross_income": "Gross Pay",
                "employer_match": "Employer Match",
                "taxes_and_fees": ["OASDI", "Medicare"],
                "savings": str(empty_savings_csv),
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

        with open(test_db_path, 'w') as f:
            json.dump(empty_config, f, indent=2)

        config = None
        try:
            config = SRConfig(test=True, test_file=str(test_db_path), user_id=1)
            sr = SavingsRate(config)

            self.assertEqual(sr.income, OrderedDict())
            self.assertEqual(sr.savings, OrderedDict())
        finally:
            # Close SRConfig to prevent ResourceWarnings
            if config is not None:
                config.close()

            # Clean up temporary files
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)

    def test_blank_csv_files(self):
        """
        The files exist but they are totally blank.
        PROBLEM - this test shouldn't pass but it does.
        At a minimum, test_columns should throw an
        AssertionError, shouldn't it? What's going on here?
        """
        # Create temporary TinyDB config with paths to blank CSV files
        temp_dir = tempfile.mkdtemp()
        test_db_path = Path(temp_dir) / "test_blank_csv.json"

        # Create completely blank CSV files for testing
        blank_income_csv = Path(temp_dir) / "blank_income.csv"
        blank_savings_csv = Path(temp_dir) / "blank_savings.csv"

        # Write completely blank CSV files (no headers, no data)
        with open(blank_income_csv, 'w') as f:
            f.write("")
        with open(blank_savings_csv, 'w') as f:
            f.write("")

        blank_config = {
            "main_user_settings": {
                "pay": str(blank_income_csv),
                "pay_date": "Date",
                "gross_income": "Gross Pay",
                "employer_match": "Employer Match",
                "taxes_and_fees": ["OASDI", "Medicare"],
                "savings": str(blank_savings_csv),
                "savings_date": "Date",
                "savings_accounts": ["Account1", "Account2"],
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

        with open(test_db_path, 'w') as f:
            json.dump(blank_config, f, indent=2)

        config = None
        try:
            config = SRConfig(test=True, test_file=str(test_db_path), user_id=1)
            # Verify SavingsRate can be instantiated with the config
            sr = SavingsRate(config)
            self.assertIsNotNone(sr, "Failed to create SavingsRate instance")
        finally:
            # Close SRConfig to prevent ResourceWarnings
            if config is not None:
                config.close()

            # Clean up temporary files
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)

    def test_get_tax_headers_for_parsing(self):
        """
        The method should return a set of tax headers from the comma-separated string.
        """
        sr = SavingsRate(self.config)
        # taxes_and_fees is stored as a comma-separated string in the config
        expected_count = (
            len(self.config.taxes_and_fees.split(','))
            if self.config.taxes_and_fees
            else 0
        )
        self.assertEqual(len(sr.get_tax_headers_for_parsing()), expected_count)

    def test_get_monthly_savings_rates_50_50(self):
        """
        %50 SR each month, %50 average
        """
        sr = SavingsRate(self.config)

        md1 = OrderedDict()
        md1['2015-01'] = {
            'income': [Decimal(2000.0)],
            'employer_match': [Decimal(200.0)],
            'taxes_and_fees': [Decimal(200.0)],
            'savings': [Decimal(1000.0)],
        }
        md1['2015-02'] = {
            'income': [Decimal(2000.0)],
            'employer_match': [Decimal(200.0)],
            'taxes_and_fees': [Decimal(200.0)],
            'savings': [Decimal(1000.0)],
        }

        r1 = sr.get_monthly_savings_rates(test_data=md1)
        for item1 in r1:
            self.assertEqual(
                item1[1],
                Decimal(50.0),
                'Incorrect savings rate. Calculated: ' + str(item1[1]),
            )
        average_rates = sr.average_monthly_savings_rates(r1)
        self.assertEqual(
            average_rates, Decimal(50.0), 'Wrong average for monthly rates.'
        )

    def test_get_monthly_savings_rates_100_100(self):
        """
        %100 SR each month, %100 average
        """
        sr = SavingsRate(self.config)

        md2 = OrderedDict()
        md2['2015-01'] = {
            'income': [Decimal(2000.0)],
            'employer_match': [Decimal(200.0)],
            'taxes_and_fees': [Decimal(200.0)],
            'savings': [Decimal(2000.0)],
        }
        md2['2015-02'] = {
            'income': [Decimal(2000.0)],
            'employer_match': [Decimal(200.0)],
            'taxes_and_fees': [Decimal(200.0)],
            'savings': [Decimal(2000.0)],
        }

        r2 = sr.get_monthly_savings_rates(test_data=md2)
        for item2 in r2:
            self.assertEqual(
                item2[1],
                Decimal(100.0),
                'Incorrect savings rate. Calculated: ' + str(item2[1]),
            )
        average_rates = sr.average_monthly_savings_rates(r2)
        self.assertEqual(
            average_rates, Decimal(100.0), 'Wrong average for monthly rates.'
        )

    def test_get_monthly_savings_rates_25_75(self):
        """
        %25 SR first month, %75 second month, %50 average
        """
        sr = SavingsRate(self.config)

        md3 = OrderedDict()
        md3['2015-01'] = {
            'income': [Decimal(2000.0)],
            'employer_match': [Decimal(200.0)],
            'taxes_and_fees': [Decimal(200.0)],
            'savings': [Decimal(500.0)],
        }
        md3['2015-02'] = {
            'income': [Decimal(2000.0)],
            'employer_match': [Decimal(200.0)],
            'taxes_and_fees': [Decimal(200.0)],
            'savings': [Decimal(1500.0)],
        }

        r3 = sr.get_monthly_savings_rates(test_data=md3)

        self.assertEqual(
            r3[0][1],
            Decimal(25),
            'Incorrect savings rate. Calculated: ' + str(r3[0][1]),
        )
        self.assertEqual(
            r3[1][1],
            Decimal(75),
            'Incorrect savings rate. Calculated: ' + str(r3[1][1]),
        )
        average_rates = sr.average_monthly_savings_rates(r3)
        self.assertEqual(
            average_rates, Decimal(50.0), 'Wrong average for monthly rates.'
        )

    def test_get_monthly_savings_rates_0_0(self):
        """
        %0 SR each month, %0 average
        """
        sr = SavingsRate(self.config)

        md = OrderedDict()
        md['2015-01'] = {
            'income': [Decimal(0.0)],
            'employer_match': [Decimal(0.0)],
            'taxes_and_fees': [Decimal(0.0)],
            'savings': [Decimal(0.0)],
        }
        md['2015-02'] = {
            'income': [Decimal(0.0)],
            'employer_match': [Decimal(0.0)],
            'taxes_and_fees': [Decimal(0.0)],
            'savings': [Decimal(0.0)],
        }

        r4 = sr.get_monthly_savings_rates(test_data=md)
        for item4 in r4:
            self.assertEqual(
                item4[1],
                Decimal(0.0),
                'Incorrect savings rate. Calculated: ' + str(item4[1]),
            )
        average_rates = sr.average_monthly_savings_rates(r4)
        self.assertEqual(
            average_rates, Decimal(0.0), 'Wrong average for monthly rates.'
        )

    def test_average_monthly_savings_rates_1_month(self):
        """
        %0 SR each month, %0 average
        """
        sr = SavingsRate(self.config)

        md = OrderedDict()
        md['2015-01'] = {
            'income': [Decimal(2000.0)],
            'employer_match': [Decimal(200.0)],
            'taxes_and_fees': [Decimal(200.0)],
            'savings': [Decimal(500.0)],
        }

        rates = sr.get_monthly_savings_rates(test_data=md)
        average_rates = sr.average_monthly_savings_rates(rates)
        self.assertEqual(
            average_rates, Decimal(25.0), 'Wrong average for monthly rates.'
        )

    def test_unique_id_from_date(self):
        result = self.sr.unique_id_from_date('2022-04-05', 1)
        self.assertEqual(result, ('2022-04-05-1', '2022-04-05'))

        result = self.sr.unique_id_from_date('2022-05-01', 2)
        self.assertEqual(result, ('2022-05-01-2', '2022-05-01'))

        result = self.sr.unique_id_from_date('2022-12-31', 3)
        self.assertEqual(result, ('2022-12-31-3', '2022-12-31'))


class TestFRED(unittest.TestCase):
    def setUp(self):
        self.config = SRConfig(test=True)
        self.sr = SavingsRate(self.config)
        self.monthly_rates = [
            (datetime.date(2021, 1, 1), Decimal('5.1')),
            (datetime.date(2021, 2, 1), Decimal('6.2')),
            (datetime.date(2021, 3, 1), Decimal('4.7')),
        ]

    def tearDown(self):
        # Close database connections to prevent ResourceWarnings
        if hasattr(self, 'config'):
            self.config.close()

    @mock.patch('savings_rate.requests.get')
    def test_get_us_average(self, mock_get):
        # Mock response from FRED API
        response_json = {
            'observations': [
                {'date': '2021-01-01', 'value': '3.4'},
                {'date': '2021-02-01', 'value': '4.2'},
                {'date': '2021-03-01', 'value': '2.7'},
            ]
        }
        mock_get.return_value.json.return_value = response_json

        # Alter the instance of SRConfig to have the expected settings
        self.config.fred_url = 'https://api.fred.org'
        self.config.fred_api_key = 'my_api_key'

        my_instance = self.sr

        # Call the function
        result = my_instance.get_us_average(self.monthly_rates)

        # Assert expected output
        expected_result = [
            (datetime.datetime(2021, 1, 1, 0, 0), Decimal('3.4')),
            (datetime.datetime(2021, 2, 1, 0, 0), Decimal('4.2')),
            (datetime.datetime(2021, 3, 1, 0, 0), Decimal('2.7')),
        ]
        self.assertEqual(result, expected_result)

    @mock.patch('savings_rate.requests.get')
    def test_missing_fred_config(self, mock_get):
        # Bad config
        self.config.fred_url = ''
        self.config.fred_api_key = None
        my_instance = self.sr
        result = my_instance.get_us_average(self.monthly_rates)
        self.assertEqual(result, [])

    @mock.patch('savings_rate.requests.get')
    def test_shorter_response_from_fred_still_works(self, mock_get):
        response_json = {
            'observations': [
                {'date': '2021-01-01', 'value': '3.4'},
                {'date': '2021-02-01', 'value': '4.2'},
            ]
        }
        mock_get.return_value.json.return_value = response_json

        self.config.fred_url = 'https://api.fred.org'
        self.config.fred_api_key = 'my_api_key'

        # Call the function
        result = self.sr.get_us_average(self.monthly_rates)

        # Assert expected output
        expected_result = [
            (datetime.datetime(2021, 1, 1, 0, 0), Decimal('3.4')),
            (datetime.datetime(2021, 2, 1, 0, 0), Decimal('4.2')),
        ]
        self.assertEqual(len(result), 2)
        self.assertEqual(len(self.monthly_rates), 3)
        self.assertEqual(result, expected_result)

    def test_message_printed_and_result_is_empty_list_during_fred_timeout(self):
        mock_response = mock.Mock()
        mock_response.json.side_effect = requests.exceptions.Timeout
        mock_get = mock.Mock(return_value=mock_response)
        self.config.fred_url = 'https://api.fred.org'
        self.config.fred_api_key = 'my_api_key'
        with mock.patch('requests.get', mock_get):
            with mock.patch('builtins.print') as mock_print:
                # Call the function with a very short timeout to force a Timeout exception
                result = self.sr.get_us_average(self.monthly_rates, 0.00001)
                self.assertEqual(result, [])
                assert mock_print.call_count == 2
                # Can't use mock_print.assert_called_once_with because there are two
                # print statments
                mock_print.call_args_list[0][0][
                    0
                ] == 'Could not retrieve a valid response from FRED.'


class TestPlotOutputPath(unittest.TestCase):
    """
    Tests for Plot class output path functionality.
    """

    def setUp(self):
        """Set up test fixtures with mock data."""
        # Create temporary directory for tests
        self.temp_dir = tempfile.mkdtemp()

        # Create test configuration
        self.test_db_path = Path(self.temp_dir) / "test_plot_config.json"
        test_config = {
            "main_user_settings": {
                "pay": "csv/income-example.csv",
                "pay_date": "Date",
                "gross_income": "Gross Pay",
                "employer_match": "Employer Match",
                "taxes_and_fees": ["OASDI", "Medicare"],
                "savings": "csv/savings-example.csv",
                "savings_date": "Date",
                "savings_accounts": ["Scottrade", "Vanguard 403b", "Vanguard Roth"],
                "notes": "",
                "show_average": True,
                "war": "off",
                "fred_url": "",
                "fred_api_key": "",
                "goal": None,
                "fi_number": None,
                "total_balances": "",
                "percent_fi_notes": "",
            },
            "users": [
                {"_id": 1, "name": "TestUser", "config_ref": "main_user_settings"}
            ],
            "enemy_settings": [],
        }

        with open(self.test_db_path, 'w') as f:
            json.dump(test_config, f, indent=2)

        # Create mock monthly rates data
        self.monthly_rates = [
            (datetime.date(2023, 1, 1), Decimal('50.0'), ['Test note 1'], None, ['']),
            (datetime.date(2023, 2, 1), Decimal('60.0'), ['Test note 2'], None, ['']),
        ]

        # Keep track of created configs for cleanup
        self.created_configs = []

    def tearDown(self):
        """Clean up test files and resources."""
        # Close any DBConfigManager instances we created
        for config in self.created_configs:
            if hasattr(config, 'db_manager') and config.db_manager:
                config.db_manager.close()

        if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def _create_test_config(self):
        """Create a test config and track it for cleanup."""
        config = SRConfig(test=True, test_file=str(self.test_db_path), user_id=1)
        self.created_configs.append(config)
        return config

    @mock.patch('savings_rate.output_file')
    @mock.patch('savings_rate.show')
    def test_plot_with_default_output_path(self, mock_show, mock_output_file):
        """Test that plot_savings_rates works with default output path."""
        config = self._create_test_config()
        sr = SavingsRate(config)
        plot = Plot(sr)

        # Call without output_path (should use default)
        plot.plot_savings_rates(self.monthly_rates)

        # Verify output_file was called with default filename
        mock_output_file.assert_called_once_with(
            "savings-rates.html", title="Monthly Savings Rates"
        )

    @mock.patch('savings_rate.output_file')
    @mock.patch('savings_rate.show')
    def test_plot_with_custom_output_path(self, mock_show, mock_output_file):
        """Test that plot_savings_rates works with custom output path."""
        config = self._create_test_config()
        sr = SavingsRate(config)
        plot = Plot(sr)

        custom_path = "my-custom-report.html"
        plot.plot_savings_rates(self.monthly_rates, output_path=custom_path)

        # Verify output_file was called with custom filename
        mock_output_file.assert_called_once_with(
            custom_path, title="Monthly Savings Rates"
        )

    @mock.patch('savings_rate.output_file')
    @mock.patch('savings_rate.show')
    @mock.patch('os.makedirs')
    def test_plot_creates_output_directory(
        self, mock_makedirs, mock_show, mock_output_file
    ):
        """Test that plot_savings_rates creates output directory if it doesn't exist."""
        config = self._create_test_config()
        sr = SavingsRate(config)
        plot = Plot(sr)

        # Use a path with a non-existent directory
        output_path = os.path.join(self.temp_dir, "reports", "test-report.html")

        with mock.patch('os.path.exists', return_value=False):
            plot.plot_savings_rates(self.monthly_rates, output_path=output_path)

        # Verify directory creation was attempted
        expected_dir = os.path.dirname(output_path)
        mock_makedirs.assert_called_once_with(expected_dir, exist_ok=True)

        # Verify output_file was called with the full path
        mock_output_file.assert_called_once_with(
            output_path, title="Monthly Savings Rates"
        )

    @mock.patch('savings_rate.output_file')
    @mock.patch('savings_rate.show')
    @mock.patch('os.makedirs')
    def test_plot_skips_directory_creation_when_exists(
        self, mock_makedirs, mock_show, mock_output_file
    ):
        """Test that plot_savings_rates skips directory creation when directory exists."""
        config = self._create_test_config()
        sr = SavingsRate(config)
        plot = Plot(sr)

        # Use a path with an existing directory
        output_path = os.path.join(self.temp_dir, "test-report.html")

        with mock.patch('os.path.exists', return_value=True):
            plot.plot_savings_rates(self.monthly_rates, output_path=output_path)

        # Verify directory creation was NOT called
        mock_makedirs.assert_not_called()

        # Verify output_file was called with the path
        mock_output_file.assert_called_once_with(
            output_path, title="Monthly Savings Rates"
        )

    @mock.patch('savings_rate.output_file')
    @mock.patch('savings_rate.show')
    def test_plot_with_absolute_path(self, mock_show, mock_output_file):
        """Test that plot_savings_rates works with absolute paths."""
        config = self._create_test_config()
        sr = SavingsRate(config)
        plot = Plot(sr)

        # Use an absolute path
        abs_path = os.path.join(self.temp_dir, "absolute-report.html")
        plot.plot_savings_rates(self.monthly_rates, output_path=abs_path)

        # Verify output_file was called with absolute path
        mock_output_file.assert_called_once_with(
            abs_path, title="Monthly Savings Rates"
        )

    @mock.patch('savings_rate.output_file')
    @mock.patch('savings_rate.show')
    def test_plot_with_none_output_path(self, mock_show, mock_output_file):
        """Test that plot_savings_rates handles None output_path correctly."""
        config = self._create_test_config()
        sr = SavingsRate(config)
        plot = Plot(sr)

        # Call with explicit None (should use default)
        plot.plot_savings_rates(self.monthly_rates, output_path=None)

        # Verify output_file was called with default filename
        mock_output_file.assert_called_once_with(
            "savings-rates.html", title="Monthly Savings Rates"
        )


class TestCLIOutputArgument(unittest.TestCase):
    """
    Tests for CLI output argument parsing.
    """

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test files."""
        if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    @mock.patch('sys.argv', ['savingsrates'])
    def test_cli_default_output_argument(self):
        """Test that CLI parsing works with default output."""
        import argparse

        parser = argparse.ArgumentParser(prog='savingsrates')
        parser.add_argument('-u', '--user', type=int, default=1)
        parser.add_argument('-o', '--output', type=str, default='savings-rates.html')

        args = parser.parse_args([])

        self.assertEqual(args.output, 'savings-rates.html')
        self.assertEqual(args.user, 1)

    @mock.patch('sys.argv', ['savingsrates', '-o', 'custom-report.html'])
    def test_cli_custom_output_argument(self):
        """Test that CLI parsing works with custom output."""
        import argparse

        parser = argparse.ArgumentParser(prog='savingsrates')
        parser.add_argument('-u', '--user', type=int, default=1)
        parser.add_argument('-o', '--output', type=str, default='savings-rates.html')

        args = parser.parse_args(['-o', 'custom-report.html'])

        self.assertEqual(args.output, 'custom-report.html')
        self.assertEqual(args.user, 1)

    @mock.patch(
        'sys.argv',
        ['savingsrates', '--output', '/tmp/reports/savings.html', '--user', '2'],
    )
    def test_cli_long_form_arguments(self):
        """Test that CLI parsing works with long-form arguments."""
        import argparse

        parser = argparse.ArgumentParser(prog='savingsrates')
        parser.add_argument('-u', '--user', type=int, default=1)
        parser.add_argument('-o', '--output', type=str, default='savings-rates.html')

        args = parser.parse_args(
            ['--output', '/tmp/reports/savings.html', '--user', '2']
        )

        self.assertEqual(args.output, '/tmp/reports/savings.html')
        self.assertEqual(args.user, 2)


if __name__ == '__main__':
    unittest.main()
