# MMM Savings Rate is an application that can parse spreadsheets and
# use the data to calculate and plot a user's savings rate over time.
# The application was inspired by Mr. Money Mustache and it uses his
# methodology to make the calculations.

# Copyright (C) 2016 Brad Busenius

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see
# <https://www.gnu.org/licenses/gpl-3.0.html/>.

import csv
import datetime
import json
import os
from collections import OrderedDict
from decimal import Decimal, InvalidOperation

import fi
import pandas as pd
import requests
from bokeh.embed import components
from bokeh.models import ColumnDataSource, DatetimeTickFormatter, HoverTool
from bokeh.plotting import figure, output_file, save, show
from dateutil import parser
from file_parsing import are_numeric, clean_strings, is_number_of_some_sort

from .db_config import DBConfigManager


class SRConfig:
    """
    Class for loading configurations to pass to the
    savings rate object.

    Args:
        user: optional, an integer representing the
        unique id of a user. Used to load specific user configurations
        from the TinyDB database. Defaults to 1 (main user).

        enemies: optional, a list of integers representing
        the unique ids of user enemies. Used to load enemy configurations
        from the TinyDB database.

        test: boolean, defaults to False. Set
        to True for testing with a custom database file.

        test_file: string, path to a test database file.
        Defaults to None and should only be set if
        test=True.
    """

    def __init__(
        self,
        user_conf_dir=None,
        user_conf=None,
        enemies=None,
        test=False,
        test_file=None,
        user_id=None,
    ):
        # Initialize database manager
        if test and test_file:
            self.db_manager = DBConfigManager(test_file)
        else:
            self.db_manager = DBConfigManager()

        # Initialize database
        if not self.db_manager.initialize_db():
            raise RuntimeError("Failed to initialize configuration database")

        # Set user ID (default to 1 if not specified)
        if user_id is not None:
            self.user_id = user_id
        else:
            self.user_id = 1  # Default to main user

        self.enemy_ids = enemies or []

        # Load configurations
        self.load_account_config()
        self.load_user_config()

        # Set the date format to use
        self.date_format = '%Y-%m-%d'

    def load_account_config(self):
        """
        Load account configurations from TinyDB.
        """
        try:
            # Get users from database
            users = self.db_manager.get_users()

            # Find the requested user (or main user by default)
            target_user = None
            for user in users:
                if user.get('_id') == self.user_id:
                    target_user = user
                    break

            if not target_user:
                raise RuntimeError(f"User with ID {self.user_id} not found in database")

            # Set user information
            self.user = [
                str(target_user['_id']),
                target_user['name'],
                target_user['config_ref'],
            ]

            # Get enemies if specified
            if self.enemy_ids:
                self.user_enemies = []
                for enemy_id in self.enemy_ids:
                    enemy_user = self.db_manager.get_user_by_id(enemy_id)
                    if enemy_user:
                        self.user_enemies.append(
                            [
                                str(enemy_user['_id']),
                                enemy_user['name'],
                                enemy_user['config_ref'],
                            ]
                        )
            else:
                # Get all other users as potential enemies
                enemies = [user for user in users if user.get('_id') != self.user_id]
                if enemies:
                    self.user_enemies = [
                        [str(enemy['_id']), enemy['name'], enemy['config_ref']]
                        for enemy in enemies
                    ]
                else:
                    self.user_enemies = None

            # Validate the loaded data
            self.validate_loaded_account_data()

        except Exception as e:
            raise RuntimeError(
                f"Failed to load account configuration from database: {e}"
            )

    def validate_loaded_account_data(self):
        """
        Validate the data loaded from the database.
        """
        # Validate main user data
        if not hasattr(self, 'user') or not self.user or len(self.user) != 3:
            raise RuntimeError(
                'Main user data is invalid. Expected [id, name, config_ref] format.'
            )

        # Collect user IDs to check for uniqueness
        user_ids = set()
        current_user_id = self.user[0]
        user_ids.add(current_user_id)

        # Validate enemy data if present
        if self.user_enemies:
            for i, enemy in enumerate(self.user_enemies):
                if len(enemy) != 3:
                    raise RuntimeError(
                        f'Enemy {i + 1} data is invalid. Expected [id, name, config_ref] format.'
                    )

                enemy_id = enemy[0]
                if enemy_id in user_ids:
                    raise RuntimeError(f'Duplicate user ID: {enemy_id}')
                user_ids.add(enemy_id)

    def load_user_config(self):
        """
        Load user configurations from TinyDB.
        """
        try:
            # Get user settings based on user ID
            if self.user_id == 1:
                # Main user settings
                settings = self.db_manager.get_main_user_settings()
            else:
                # Enemy user settings
                settings = self.db_manager.get_enemy_settings(self.user_id)
                if not settings:
                    raise RuntimeError(
                        f"Enemy settings not found for user ID {self.user_id}"
                    )

            # Validate the settings
            self.validate_user_settings(settings)

            # Set configuration attributes from database
            self.savings_source = settings['savings']
            self.savings_source_type = self.file_extension(self.savings_source)

            self.pay_source = settings['pay']
            self.pay_source_type = self.file_extension(self.pay_source)

            self.war_mode = settings['war'] == 'on'

            self.gross_income = settings['gross_income']
            self.employer_match = settings['employer_match']

            # Handle list fields
            if isinstance(settings['taxes_and_fees'], list):
                self.taxes_and_fees = ','.join(settings['taxes_and_fees'])
            else:
                self.taxes_and_fees = settings['taxes_and_fees']

            if isinstance(settings['savings_accounts'], list):
                self.savings_accounts = ','.join(settings['savings_accounts'])
            else:
                self.savings_accounts = settings['savings_accounts']

            self.pay_date = settings['pay_date']
            self.savings_date = settings['savings_date']

            # Required columns for spreadsheets
            self.required_income_columns = set(
                [self.gross_income, self.employer_match, self.pay_date]
            ).union(clean_strings(set(self.taxes_and_fees.split(','))))
            self.required_savings_columns = set([self.savings_date]).union(
                set(clean_strings(self.savings_accounts.split(',')))
            )

            # Load additional configuration settings
            self.fred_url = settings.get('fred_url', '')
            self.fred_api_key = settings.get('fred_api_key', '')
            self.notes = settings.get('notes', '')
            self.percent_fi_notes = settings.get('percent_fi_notes', '')
            self.show_average = settings.get('show_average', True)

            # Load and validate numeric fields with error handling
            self.goal = self._load_numeric_config(settings, 'goal')
            self.fi_number = self._load_numeric_config(settings, 'fi_number')
            self.total_balances = settings.get('total_balances', False)

        except Exception as e:
            raise RuntimeError(f"Failed to load user configuration from database: {e}")

    def close(self):
        """
        Close the database connection to free resources.
        """
        if hasattr(self, 'db_manager') and self.db_manager is not None:
            self.db_manager.close()

    def __enter__(self):
        """
        Context manager entry. Enables usage with 'with' statements.

        Example:
            with SRConfig(user_id=1) as config:
                settings = config.get_main_user_settings()
            # Database connections and logging handlers automatically closed here
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Context manager exit - automatically calls close() to clean up database connections.
        This prevents ResourceWarnings from unclosed database and logging handlers.
        """
        self.close()

    def _load_numeric_config(self, settings, field_name):
        """
        Load and validate a numeric configuration field.
        Returns False and prints error message if value is not numeric.
        """
        value = settings.get(field_name)
        if value is None:
            return False

        # If it's already a number, return it
        if isinstance(value, (int, float)):
            return value

        # Try to convert string to number
        if isinstance(value, str):
            try:
                # Try float first, then int
                if '.' in value:
                    return float(value)
                else:
                    return int(value)
            except ValueError:
                print(f"The value for '{field_name}' should be numeric, e.g. 65.")
                return False

        # For any other type, print error and return False
        print(f"The value for '{field_name}' should be numeric, e.g. 65.")
        return False

    def validate_user_settings(self, settings):
        """
        Validate user settings loaded from TinyDB.

        Args:
            settings: Dict containing user settings from database.
        """
        from .db_config import REQUIRED_MAIN_USER_FIELDS

        for field in REQUIRED_MAIN_USER_FIELDS:
            if field not in settings:
                raise AssertionError(
                    f"Missing required field in user settings: {field}"
                )

        # Validate file paths exist
        if not os.path.exists(settings['pay']):
            print(f"Warning: Pay file does not exist: {settings['pay']}")
        if not os.path.exists(settings['savings']):
            print(f"Warning: Savings file does not exist: {settings['savings']}")

    def has_fred(self):
        """
        Test if the needed config exists to enable FRED.

        Returns:
            bool
        """
        return bool(self.fred_api_key and self.fred_url)

    def file_extension(self, string):
        """
        Gets a file extension from a string that ends in a file name.

        Args:
            string (str): File name, e.g. foobar.txt.

        Returns:
            str: File extension, e.g. .txt.
        """
        return os.path.splitext(string)[1]


class SavingsRate:
    """
    Class for getting and calculating a monthly savings rate
    based on information about monthly pay and spending.
    """

    def __init__(self, config):
        """
        Initialize the object with settings from the config file.

        Args:
            config: object
        """

        # Load the configurations
        self.config = config

        # Load income and savings information
        self.get_pay()
        self.get_savings()

    def test_columns(self, row, spreadsheet):
        """
        Make sure the required columns are present for different
        types of spreadsheets, ensure that what was mapped in the
        config.ini exists as a column header in the spreadsheet.

        Args:
            row: a set representing column headers from a spreadsheet.

            spreadsheet: string, the type of spreadsheet to validate.
            Possible values are "income" or "savings".

        Returns:
            None, throws an AssertionError if spreadsheet column names
            don't match what was set in the configuration. Raises a
            ValueError if a bad argument is passed.
        """

        required = {
            'income': self.config.required_income_columns,
            'savings': self.config.required_savings_columns,
        }

        if spreadsheet in required:
            val = row.issuperset(required[spreadsheet])
        else:
            msg = (
                'You passed an improper spreadsheet type to test_columns(). '
                + 'Possible values are "income" and "savings"'
            )
            raise ValueError(msg)

        assert val is True, (
            'The '
            + spreadsheet
            + ' spreadsheet is missing a column header. '
            + 'The following columns were configured: '
            + str(required[spreadsheet])
            + ' '
            + 'but these column headings were found in the spreadsheet: '
            + str(row)
        )

    def get_pay(self):
        """
        Loads payment data from a .csv fle.

        Args:
            None

        Returns:
        """
        ext = self.config.pay_source_type
        if ext == '.csv':
            return self.load_pay_from_csv()
        elif ext == '.xlsx':
            return self.load_pay_from_xlsx()
        else:
            raise RuntimeError('Problem loading income information!')

    def clean_num(self, number):
        """
        Looks at numeric values to determine if they are numeric.
        Converts empty strings and null values to 0.0. Acceptable
        arguments are None, empty string, int, float, or decimal.

        Args:
            number: Float, int, decimal, empty string, or null value.

        Returns:
            float, int, or decimal
        """
        try:
            number = number.strip()
        except AttributeError:
            pass
        if number is None or number == '':
            retval = 0.0
        elif is_number_of_some_sort(number):
            retval = number
        else:
            raise TypeError(
                'A numeric value was expected. The argument passed was non-numeric.'
            )
        return retval

    def load_pay_from_csv(self):
        """
        Loads a paystub from a .csv file.

        Args:
            None

        Returns:
            None
        """
        with open(self.config.pay_source) as csvfile:
            retval = OrderedDict()
            reader = csv.DictReader(csvfile)
            count = 0
            for row in reader:
                # Make sure required columns are in the spreadsheet
                self.test_columns(set(row.keys()), 'income')
                date_string = row[self.config.pay_date]
                unique_id = self.unique_id_from_date(date_string, count)[0]
                retval[unique_id] = row
                count += 1
            self.income = retval

    def load_pay_from_xlsx(self):
        """
        Loads a paystub from an Excel stylesheet. Converts rows into a
        format similar to what we get in csv.DictReader before crosswalking
        them into the needed format.

        Args:
            None

        Returns
            None
        """
        retval = OrderedDict()
        df = pd.read_excel(self.config.pay_source, dtype=str, na_filter=False)
        self.test_columns(set(df.columns.to_list()), 'income')
        count = 0
        for row in df.itertuples():
            date_string = row.__getattribute__(self.config.pay_date)
            unique_id = self.unique_id_from_date(date_string, count)[0]
            columns = list(df.columns)
            row_dict = dict(zip(columns, row[1:]))
            retval[unique_id] = row_dict
            count += 1
        self.income = retval

    def get_savings(self):
        """
        Get savings data from designated source.

        Args:
            None
        """
        ext = self.config.pay_source_type
        if ext == '.csv':
            return self.load_savings_from_csv()
        elif ext == '.xlsx':
            return self.load_savings_from_xlsx()
        else:
            raise RuntimeError('Problem loading savings information!')

    def load_savings_from_csv(self):
        """
        Loads savings data from a .csv file.

        Args:
            None

        Returns:
            None
        """
        with open(self.config.savings_source) as csvfile:
            retval = OrderedDict()
            reader = csv.DictReader(csvfile)
            count = 0
            for row in reader:
                # Make sure required columns are in the spreadsheet
                self.test_columns(set(row.keys()), 'savings')
                date_string = row[self.config.savings_date]
                unique_id = self.unique_id_from_date(date_string, count)[0]
                retval[unique_id] = row
                count += 1
            self.savings = retval

    def unique_id_from_date(self, date_string, count):
        """
        Dates are important when calculating monthly savings rates.
        This function formats the date and generates a unique id. Both
        of these are used to keep track of and organize savings and
        income related data.

        Args:
            date_string: date string.
            count: int

        Returns:
            tuple(str, str): where the first item is a unique id and the
            second item is a date string.
        """
        dt_obj = parser.parse(date_string)
        date = dt_obj.strftime(self.config.date_format)
        unique_id = date + '-' + str(count)
        return (unique_id, date)

    def load_savings_from_xlsx(self):
        """
        Loads savings data from an Excel stylesheet. Converts rows into a
        format similar to what we get in csv.DictReader before crosswalking
        them into the needed format.

        Args:
            None

        Returns
            None
        """
        sdata = OrderedDict()
        df = pd.read_excel(self.config.savings_source, dtype=str, na_filter=False)
        self.test_columns(set(df.columns.to_list()), 'savings')
        count = 0
        for row in df.itertuples():
            date_string = row.__getattribute__(self.config.savings_date)
            unique_id = self.unique_id_from_date(date_string, count)[0]
            columns = list(df.columns)
            row_dict = dict(zip(columns, row[1:]))
            sdata[unique_id] = row_dict
            count += 1
        self.savings = sdata

    def get_tax_headers_for_parsing(self):
        """
        Get the .csv column headers used for tracking taxes and fees
        in the income related spreadsheet.

        Args:
            None

        Returns:
            Set of accounts used for tracking savings.
        """
        # Get taxes_and_fees from TinyDB configuration
        # Note: taxes_and_fees is always a string after load_user_config() processing
        taxes_and_fees = self.config.taxes_and_fees
        if taxes_and_fees and isinstance(taxes_and_fees, str):
            return set(taxes_and_fees.split(','))
        else:
            return set()

    def get_monthly_data(self):
        """
        Crosswalk the data for income and spending into a structure
        representing one month time periods. Returns an OrderedDict.

        Args:
            None

        Returns:
            OrderedDict

        Example return data:
            OrderedDict([
                ('2015-02', {'income': [Decimal('4833.34')],
                             'employer_match': [Decimal('120.84')],
                             'taxes_and_fees': [Decimal('814.70')],
                             'notes': {''},
                             'savings': [Decimal('1265.85')],
                             'percent_fi_notes': {''},
                             'percent_fi': [4.450954]}),
                ('2015-03', {'income': [Decimal('4833.34')],
                             'employer_match': [Decimal('120.84')],
                             'taxes_and_fees': [Decimal('814.70')],
                             'notes': {''},
                             'savings': [Decimal('1115.85')],
                             'percent_fi_notes': {''},
                             'percent_fi': [4.500051999999999]}),
        """
        income = self.income.copy()
        savings = self.savings.copy()

        # For this data structure
        date_format = '%Y-%m'

        # Column headers used for tracking taxes and fees
        taxes = self.get_tax_headers_for_parsing()

        # Dataset to return
        sr = OrderedDict()

        # Loop over income and savings
        for payout in income:
            # Structure the date
            date_string = str(income[payout][self.config.pay_date])
            date_string_obj = parser.parse(date_string)
            new_date_string = date_string_obj.strftime(self.config.date_format)
            pay_dt_obj = datetime.datetime.strptime(
                new_date_string, self.config.date_format
            )
            pay_month = pay_dt_obj.strftime(date_format)

            # Get income data for inclusion, cells containing blank
            # strings are converted to zeros.
            income_gross = (
                0
                if income[payout][self.config.gross_income] == ''
                else income[payout][self.config.gross_income]
            )
            income_match = (
                0
                if income[payout][self.config.employer_match] == ''
                else income[payout][self.config.employer_match]
            )
            income_taxes = [
                0 if income[payout][val] == '' else income[payout][val]
                for val in clean_strings(self.config.taxes_and_fees.split(','))
            ]

            # Validate income spreadsheet data
            assert are_numeric([income_gross, income_match]) is True
            assert are_numeric(income_taxes) is True

            # If the data passes validation, convert it (strings to Decimal objects)
            gross = Decimal(income_gross)
            employer_match = Decimal(income_match)
            taxes = sum([Decimal(tax) for tax in income_taxes])

            # ---Build the datastructure---

            # Set main dictionary key, encapsulte data by month
            sr.setdefault(pay_month, {})

            # Set income related qualities for the month
            sr[pay_month].setdefault('income', []).append(gross)
            sr[pay_month].setdefault('employer_match', []).append(employer_match)
            sr[pay_month].setdefault('taxes_and_fees', []).append(taxes)

            # Add an income note if there is one
            try:
                inote = income[payout][self.config.notes]
            except KeyError:
                inote = ''
            sr[pay_month].setdefault('notes', set()).add(inote)

            if 'savings' not in sr[pay_month]:
                for transfer in savings:
                    tran_date_string = str(savings[transfer][self.config.savings_date])
                    tran_date_string_obj = parser.parse(tran_date_string)
                    tran_month = tran_date_string_obj.strftime(date_format)

                    if tran_month == pay_month:

                        # Define savings data for inclusion
                        bank = [
                            savings[transfer][val]
                            for val in clean_strings(
                                self.config.savings_accounts.split(',')
                            )
                            if savings[transfer][val] != ''
                        ]

                        # Validate savings spreadsheet data
                        assert are_numeric(bank) is True

                        # If the data passes validation, convert it (strings to Decimal objects)
                        money_in_the_bank = sum(
                            [Decimal(investment) for investment in bank]
                        )

                        # Set spending related qualities for the month
                        sr[pay_month].setdefault('savings', []).append(
                            money_in_the_bank
                        )

                        # Add a savings note if there is one
                        try:
                            snote = savings[transfer][self.config.notes]
                        except KeyError:
                            snote = ''
                        sr[pay_month].setdefault('notes', set()).add(snote)

                        # % FI note
                        try:
                            pfi_note = savings[transfer][self.config.percent_fi_notes]
                        except KeyError:
                            pfi_note = ''
                        sr[pay_month].setdefault('percent_fi_notes', set()).add(
                            pfi_note
                        )

                        # Calculate % FI
                        if self.config.total_balances:
                            total_balances = savings[transfer][
                                self.config.total_balances
                            ]
                            if total_balances and self.config.fi_number:
                                percent_fi = fi.get_percentage(
                                    total_balances, self.config.fi_number
                                )
                                sr[pay_month].setdefault('percent_fi', []).append(
                                    percent_fi
                                )
                        else:
                            sr[pay_month].setdefault('percent_fi', []).append(
                                float('nan')
                            )
        return sr

    def get_monthly_savings_rates(self, test_data=False):
        """
        Calculates the monthly savings rates over a period of time.

        Args:
            test_data: OrderedDict or boolean, for passing in test data.
            Defaults to false.

        Returns:
            list: a list of tuples where each tuple contains:
                - datetime object: python date object.
                - Decimal: The savings rate for the month.
                - set: strings, optional notes or event.
                - float: % FI if enabled.
                - set: string note related to the % FI plot.
        """
        if not test_data:
            monthly_data = self.get_monthly_data()
        else:
            monthly_data = test_data

        monthly_savings_rates = []
        for month in monthly_data:
            pay = fi.take_home_pay(
                sum(monthly_data[month]['income']),
                sum(monthly_data[month]['employer_match']),
                monthly_data[month]['taxes_and_fees'],
            )
            savings = (
                sum(monthly_data[month]['savings'])
                if 'savings' in monthly_data[month]
                else 0
            )

            try:
                note = monthly_data[month]['notes']
            except KeyError:
                note = ''

            spending = pay - savings
            try:
                srate = fi.savings_rate(pay, spending)
            except InvalidOperation:
                srate = Decimal(0)

            try:
                percent_fi = monthly_data[month]['percent_fi']
            except KeyError:
                percent_fi = None

            try:
                pfi_note = monthly_data[month]['percent_fi_notes']
            except KeyError:
                pfi_note = ''

            date = datetime.datetime.strptime(month, '%Y-%m')
            monthly_savings_rates.append((date, srate, note, percent_fi, pfi_note))

        return monthly_savings_rates

    def get_us_average(self, monthly_rates, timeout=4):
        """
        Get the average monthly savings rates. The data is
        pulled from the Federal Reserve Economic Data, FRED
        by the Research Department at the Federal Reserve
        Bank of St. Louis

        Args:
            monthly_rates: a list of tuples where the
            first item in each tupal is a python date
            object and the second item in each tuple
            is the savings rate for that month. These
            are the savings rates that belong to the
            user.

            timeout: float or int.

        Returns:
            A list of tuples where the first item in each
            tupal is a python date object and the second
            item in each tuple is the savings rate for
            that month.
        """
        if self.config.has_fred():
            start_date = (
                monthly_rates[0:1][0][0]
                .replace(day=1)
                .strftime(self.config.date_format)
            )
            end_date = (
                monthly_rates[-1:][0][0]
                .replace(day=1)
                .strftime(self.config.date_format)
            )
            url = self.config.fred_url
            params = {
                'api_key': self.config.fred_api_key,
                'observation_start': start_date,
                'observation_end': end_date,
            }
            try:
                response = requests.get(f'{url}', params=params, timeout=timeout)
            except (
                requests.exceptions.MissingSchema,
                requests.exceptions.InvalidSchema,
            ) as e:
                print(f'Bad url for fred_url. {str(e)}')
                return []
            try:
                if response.status_code == 400 or response.status_code == 404:
                    raise requests.exceptions.HTTPError()
                response_json = response.json()
            except (
                AttributeError,
                json.decoder.JSONDecodeError,
                requests.exceptions.HTTPError,
                requests.exceptions.Timeout,
            ):
                print('Could not retrieve a valid response from FRED.')
                if response.text:
                    response_txt = response.text.replace('\\', '')
                    print(f'Bad request: {response_txt}')
                return []

            average_us_savings_rates = []
            for row in response_json['observations']:
                date_obj = datetime.datetime.strptime(
                    row['date'], self.config.date_format
                )
                savings_rate = Decimal(row['value'])
                monthly_rate = (date_obj, savings_rate)
                average_us_savings_rates.append(monthly_rate)
            return average_us_savings_rates
        return []

    def average_monthly_savings_rates(self, monthly_rates):
        """
        Calculates the average monthly savings rate
        for a period of months.

        Args:
            monthly_rates: a list of tuples where the
            first item in each tupal is a python date
            object and the second item in each tuple
            is the savings rate for that month.

        Returns:
            float
        """
        nums = [rate[1] for rate in monthly_rates]
        return float(Decimal(sum(nums)) / len(nums))


class Plot:
    """
    A class for plotting the monthly savings rates for an individual
    and his or her enemies.
    """

    def __init__(self, user):
        """
        Initialize the object.
        """
        # Load the user as a savings_rate object
        self.user = user

        # Colors for plotting enemy graphs
        self.colors = [
            '#B30000',
            '#E34A33',
            '#8856a7',
            '#4D9221',
            '#404040',
            '#9E0142',
            '#0C2C84',
            '#810F7C',
        ]

    def plot_savings_rates(
        self, monthly_rates, embed=False, output_path=None, no_browser=False
    ):
        """
        Plots the monthly savings rates for a period of time.

        Args:
            monthly_rates: a list of tuples where the first item in each
            tupal is a python date object and the second item in each
            tuple is the savings rate for that month.

            embed, boolean defaults to False. Setting to true returns a
            plot for embedding in a web application.

            output_path, string defaults to None. If provided, specifies
            the path where the HTML file should be saved. If None, defaults
            to "savings-rates.html".

            no_browser, boolean defaults to False. If True, saves HTML file
            without opening browser (useful for testing).

        Returns:
            None
        """

        # Convenience variables
        average_rate = self.user.average_monthly_savings_rates(monthly_rates)
        colors = list(self.colors)

        # Prepare the data
        x = []
        y = []
        notes = []
        y_offset = []
        percent_fi = []
        percent_fi_x = []
        percent_fi_notes = []
        for i, data in enumerate(monthly_rates):
            x.append(data[0])
            # Must cast Decimal to float because Bokeh cannot serialize Decimals anymore
            y.append(float(data[1]))
            # Only separate notes with a line break if there are more than one and they aren't empty
            notes.append('\n'.join(data[2]).strip('\n'))
            percent_fi_notes.append(''.join(data[4]).strip())
            # Display text below the point if it's a drop for a better chance at good formatting
            if data[1] < monthly_rates[i - 1][1]:
                y_offset.append(25)
            else:
                y_offset.append(-5)
            if data[3]:
                percent_fi.append(data[3])
                percent_fi_x.append(data[0])

        # Output to static HTML file
        if output_path is None:
            output_path = "savings-rates.html"

        # Ensure output directory exists
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)

        output_file(output_path, title="Monthly Savings Rates")

        # Create a plot with a title and axis labels
        p = figure(
            title="Monthly Savings Rates",
            y_axis_label='% of take home pay',
            x_axis_type="datetime",
        )
        p.toolbar.logo = None

        p.below[0].formatter = DatetimeTickFormatter(
            years='%Y', months='%b %Y', days='%b %d %Y'
        )

        # Add a line renderer with legend and line thickness
        p.line(x, y, legend_label="My savings rate", line_width=2)
        p.scatter(x, y, size=6, marker='circle')
        inv = p.scatter(x, y, size=15, fill_alpha=0.0, line_alpha=0.0, marker='circle')

        # Tooltips for monthly savings rate
        tooltips = [
            ('Date', '@x{%m/%Y}'),
            ('Rate', '@y'),
        ]
        hover_tool = HoverTool(
            renderers=[inv],
            tooltips=tooltips,
            formatters={'@x': 'datetime'},
        )
        p.add_tools(hover_tool)

        # Plot the average monthly savings rate
        if self.user.config.show_average is True:
            p.line(
                x,
                average_rate,
                legend_label="My average rate",
                line_color="#ff6600",
                line_width=2,
                line_dash="4 4",
                line_alpha=0.8,
            )

        # Plot % FI
        if self.user.config.fi_number and self.user.config.total_balances:
            p.line(
                percent_fi_x,
                percent_fi,
                legend_label="% FI",
                line_color="#000000",
                line_width=2,
                line_alpha=0.3,
            )
            self.update_plot_with_percent_fi_notes(
                p, percent_fi, percent_fi_x, percent_fi_notes
            )

        # % FI text annotations
        # p.text(
        #    x=percent_fi_x,
        #    y=percent_fi,
        #    text=percent_fi_notes,
        #    text_color="#777777",
        #    text_align="center",
        # )

        # Savings rate text annotations
        p.text(
            x=x,
            y=y,
            text=notes,
            text_color="#333333",
            text_align="center",
            y_offset=y_offset,
        )

        # Goal
        if self.user.config.goal:
            p.line(
                x,
                self.user.config.goal,
                legend_label="Goal",
                line_color="#01D423",
                line_width=2,
                line_dash="4 4",
            )

        # Show average US savings rates if enabled.
        if self.user.config.has_fred():
            self.update_plot_for_fred(p, monthly_rates)

        # Plot the savings rate of enemies if war_mode is on
        if self.user.config.war_mode is True:
            for war in self.user.config.user_enemies:
                # Enemy mode and configuration directory should always
                # be the same as user mode and configuration directory
                enemy_mode = self.user.config.mode
                enemy_conf_dir = self.user.config.user_conf_dir

                enemy_config = SRConfig(enemy_mode, enemy_conf_dir, war[2], war[0], [])
                enemy_savings_rate = SavingsRate(enemy_config)
                enemy_rates = enemy_savings_rate.get_monthly_savings_rates()
                enemy_x = []
                enemy_y = []

                for enemy_data in enemy_rates:
                    enemy_x.append(enemy_data[0])
                    enemy_y.append(enemy_data[1])

                # Plot the monthly savings rate for enemies
                p.line(
                    enemy_x,
                    enemy_y,
                    legend_label=war[1] + '\'s savings rate',
                    line_color=colors.pop(),
                    line_width=2,
                )

                # Reset the color palette if we run out of colors
                if len(colors) == 0:
                    colors = list(self.colors)

        p.legend.location = "top_left"

        # Show the results
        if embed is False:
            p.sizing_mode = "stretch_both"
            if no_browser:
                save(p)
            else:
                show(p)
        else:
            # For embed=True, still generate HTML file if output_path is provided
            if output_path:
                # Save as standalone HTML file for GUI use - must match CLI behavior
                p.sizing_mode = "stretch_both"
                # Use save() instead of show() to prevent browser opening
                save(p)
            return components(p)

    def update_plot_for_fred(self, p, monthly_rates):
        us_average_x = []
        us_average_y = []
        average_us_savings = self.user.get_us_average(monthly_rates)
        for data in average_us_savings:
            us_average_x.append(data[0])
            us_average_y.append(float(data[1]))
        p.line(
            us_average_x,
            us_average_y,
            legend_label="US average savings",
            line_color="#9467bd",
            line_width=2,
            line_dash="4 4",
        )

    def update_plot_with_percent_fi_notes(
        self, p, percent_fi, percent_fi_x, percent_fi_notes
    ):
        non_empty_notes = [note if note != '' else None for note in percent_fi_notes]
        non_empty_notes_source = ColumnDataSource(
            data=dict(
                percent_fi_x=[
                    x
                    for x, note in zip(percent_fi_x, non_empty_notes)
                    if note is not None
                ],
                percent_fi=[
                    fi
                    for fi, note in zip(percent_fi, non_empty_notes)
                    if note is not None
                ],
                percent_fi_notes=[note for note in non_empty_notes if note is not None],
            )
        )
        p.scatter(
            x='percent_fi_x',
            y='percent_fi',
            size=6,
            color='#777777',
            source=non_empty_notes_source,
            marker='circle',
        )
        invisible_circle = p.scatter(
            x='percent_fi_x',
            y='percent_fi',
            size=40,
            fill_alpha=0.0,
            line_alpha=0.0,
            source=non_empty_notes_source,
            marker='circle',
        )
        tooltips = [
            ('', '<span style="font-size:15px;">@percent_fi_notes{safe}</span>'),
        ]
        hover_tool = HoverTool(
            renderers=[invisible_circle],
            tooltips=tooltips,
            show_arrow=False,
            mode='mouse',
        )
        hover_tool.formatters = {'@labels': 'printf'}
        p.add_tools(hover_tool)
