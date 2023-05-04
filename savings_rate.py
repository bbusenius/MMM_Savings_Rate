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

import configparser
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
from bokeh.plotting import figure, output_file, show
from dateutil import parser
from file_parsing import are_numeric, clean_strings, is_number_of_some_sort

REQUIRED_INI_ACCOUNT_OPTIONS = {'Users': ['self']}

REQUIRED_INI_USER_OPTIONS = {
    'Sources': [
        'pay',
        'pay_date',
        'gross_income',
        'employer_match',
        'taxes_and_fees',
        'savings',
        'savings_accounts',
        'savings_date',
        'war',
    ],
    'Graph': ['width', 'height'],
}


class SRConfig:
    """
    Class for loading configurations to pass to the
    savings rate object.

    Args:
        user_conf_dir: path to a directory of user .ini
        configuration files.

        user_conf: a string name of a  user .ini file.

        user: optional, an integer representing the
        unique id of a user. This is only needed when
        running as part of an application connected to
        a database. Not necessary when running with
        csv files.

        enemies: optional, a list of integers representing
        the unique ids of user enemies. Like the above, this
        is only needed when running as part of an application
        connected to a database. Not necessary when running
        with csv files.

        test: boolean, defaults to False. Set
        to True for testing the account-config.ini
        under a different name.

        test_file: string, name of an .ini to test.
        Defaults to None and should only be set if
        test=True.
    """

    def __init__(
        self,
        user_conf_dir=None,
        user_conf=None,
        user=None,
        enemies=None,
        test=False,
        test_file=None,
    ):

        self.user_conf_dir = user_conf_dir
        self.user_ini = user_conf_dir + user_conf
        self.is_test = test
        self.test_account_ini = test_file
        self.load_account_config()

        self.fred_api_key = ''
        self.fred_url = ''
        self.notes = ''
        self.percent_fi_notes = ''
        self.show_average = True
        self.goal = False
        self.fi_number = False
        self.total_balances = False

        self.load_user_config()

        # Set the date format to use
        self.date_format = '%Y-%m-%d'

    def load_account_config(self):
        """
        Wrapper function, loads configurations from
        ini files.
        """
        return self.load_account_config_from_ini()

    def load_user_config(self):
        """
        Wrapper function, load the user configurations
        from .ini files or the db
        """
        config = self.load_user_config_from_ini()
        return config

    def load_user_config_from_ini(self):
        """
        Get user configurations from .ini files.
        """
        # Get the user configurations
        self.user_config = configparser.RawConfigParser()
        config = self.user_config.read(self.user_ini)

        # Raise an exception if a user config
        # cannot be found
        if config == []:
            raise FileNotFoundError(
                'The user config is an empty []. Create a user config file and make sure it\'s referenced in account-config.ini.'
            )

        # Validate the configparser config object
        self.validate_user_ini()

        # Source of and file type of savings data (.xlsx of .csv)
        self.savings_source = self.user_config.get('Sources', 'savings')
        self.savings_source_type = self.file_extension(self.savings_source)

        # Source and file type of income data (.xlsx of .csv)
        self.pay_source = self.user_config.get('Sources', 'pay')
        self.pay_source_type = self.file_extension(self.pay_source)

        # Set war mode
        self.war_mode = self.user_config.getboolean('Sources', 'war')

        # Other spreadsheet columns we care about
        self.gross_income = self.user_config.get('Sources', 'gross_income')
        self.employer_match = self.user_config.get('Sources', 'employer_match')
        self.taxes_and_fees = self.user_config.get('Sources', 'taxes_and_fees')
        self.savings_accounts = self.user_config.get('Sources', 'savings_accounts')
        self.pay_date = self.user_config.get('Sources', 'pay_date')
        self.savings_date = self.user_config.get('Sources', 'savings_date')

        # Required columns for spreadsheets
        # Column names set in the config must exist in the .csv when we load it
        # These values are used later to ensure mappings to the .csv are correct
        self.required_income_columns = set(
            [self.gross_income, self.employer_match, self.pay_date]
        ).union(clean_strings(set(self.taxes_and_fees.split(','))))
        self.required_savings_columns = set([self.savings_date]).union(
            set(clean_strings(self.savings_accounts.split(',')))
        )
        self.load_fred_url_config()
        self.load_fred_api_key_config()
        self.load_notes_config()
        self.load_show_average_config()
        self.load_goal_config()
        self.load_fi_number_config()
        self.load_total_balances_config()

    def load_notes_config(self):
        """
        Loads the notes config from an .ini if it exists.
        """
        try:
            self.notes = self.user_config.get('Sources', 'notes')
        except (configparser.NoOptionError):
            self.notes = ''

        try:
            self.percent_fi_notes = self.user_config.get('Sources', 'percent_fi_notes')
        except (configparser.NoOptionError):
            self.percent_fi_notes = ''

    def load_total_balances_config(self):
        """
        Loads the config for a header column where users store
        their total account balances.
        """
        try:
            self.total_balances = self.user_config.get('Sources', 'total_balances')
        except (configparser.NoOptionError):
            self.total_balances = False

    def load_fred_url_config(self):
        """
        Loads the config from .ini if it exists.
        """
        try:
            self.fred_url = self.user_config.get('Sources', 'fred_url')
        except (configparser.NoOptionError):
            self.fred_url = ''

    def load_fred_api_key_config(self):
        """
        Loads the config from .ini if it exists.
        """
        try:
            self.fred_api_key = self.user_config.get('Sources', 'fred_api_key')
        except (configparser.NoOptionError):
            self.fred_api_key = ''

    def has_fred(self):
        """
        Test if the needed config exists to enable FRED.

        Returns:
            bool
        """
        return bool(self.fred_api_key and self.fred_url)

    def load_goal_config(self):
        """
        Savings rate goal the user is trying to hit.

        Args:
            None

        Returns:
            None
        """
        try:
            goal = self.user_config.get('Sources', 'goal')
            try:
                self.goal = float(goal)
            except (ValueError):
                print('The value for \'goal\' should be numeric, e.g. 65.')
        except (configparser.NoOptionError):
            self.goal = False

    def load_show_average_config(self):
        """
        Loads the config from .ini if it exists.
        """
        try:
            self.show_average = self.user_config.getboolean('Sources', 'show_average')
        except (configparser.NoOptionError):
            pass

    def load_fi_number_config(self):
        """
        FI number the user is trying to hit.

        Args:
            None

        Returns:
            None
        """
        try:
            fi_number = self.user_config.get('Sources', 'fi_number')
            try:
                self.fi_number = float(fi_number)
            except (ValueError):
                print('The value for \'fi_number\' should be numeric, e.g. 1000000.')
        except (configparser.NoOptionError):
            self.fi_number = False

    def validate_user_ini(self):
        """
        Minimum validation for the user
        config.ini when running in 'ini' mode.
        """
        # Required section and options
        for section in REQUIRED_INI_USER_OPTIONS:
            assert self.user_config.has_section(section), (
                '[' + section + '] is a required section in the user config.ini.'
            )
            for option in REQUIRED_INI_USER_OPTIONS[section]:
                assert self.user_config.has_option(section, option), (
                    'The "'
                    + option
                    + '" option is required in the ['
                    + section
                    + '] section of config.ini.'
                )

        # Assumptions about the data
        assert (
            are_numeric(
                [
                    self.user_config.get('Graph', 'width'),
                    self.user_config.get('Graph', 'height'),
                ]
            )
            is True
        ), '[Graph] width and height must contain numeric values.'

    def load_account_config_from_ini(self):
        """
        Get the configurations from an .ini file.
        Throw an exception if the file is lacking
        required data.
        """
        # Load the ini
        self.account_config = configparser.RawConfigParser()
        if not self.is_test:
            account_config = self.account_config.read(
                self.user_conf_dir + 'account-config.ini'
            )
        else:
            try:
                account_config = self.account_config.read(
                    self.user_conf_dir + self.test_account_ini
                )
            except (TypeError):
                raise RuntimeError(
                    'If test=True, a test .ini must be provided. You must provide a value for test_file.'
                )

        # Raise an exception if the account_config comes back empty
        if account_config == []:
            raise FileNotFoundError(
                'The account_config is an empty []. A file named, "account-config.ini" was not found. This file must exist.'
            )

        # Validate the ini file.
        self.validate_account_ini()

        # Crosswalk data for the main player if it
        # exists, otherwise throw an exception.
        self.user = self.account_config.get('Users', 'self').split(',')

        # If enemies isn't in the account-config.ini
        # set it to None.
        try:
            self.user_enemies = [
                enemy.split(',')
                for enemy in self.account_config.get('Users', 'enemies').split('|')
            ]
        except (KeyError, configparser.NoOptionError):
            self.user_enemies = None

        # Set a log file (optional)
        self.log = (
            self.account_config.get('Dev', 'logfile')
            if self.account_config.has_section('Dev')
            else None
        )

        # Validate the data loaded from account-config.ini
        self.validate_loaded_account_data()

    def validate_account_ini(self):
        """
        Minimum validation for account-config.ini.
        """
        # Required sections
        assert self.account_config.has_section(
            'Users'
        ), '[Users] is a required section in account-config.ini.'

        # Required options
        assert self.account_config.has_option(
            'Users', 'self'
        ), 'The "self" option is required in the [Users] section of account-config.ini.'

    def validate_loaded_account_data(self):
        """
        Validate the data loaded from
        account-config.ini.
        """
        assert (
            len(self.user) == 3
        ), 'The "self" option in the [Users] section should have an id, name, and path to user config separated by commas.'

        user_ids = set([])
        main_user_id = self.user[0]
        user_ids.add(main_user_id)

        if self.user_enemies:
            i = 1  # Self, already added
            for enemy in self.user_enemies:
                user_ids.add(enemy[0])
                assert (
                    len(enemy) == 3
                ), 'The "enemies" option in account-config.ini is not set correctly.'
                i += 1
            assert len(user_ids) == i, 'Every user ID must be unique.'

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
        except (AttributeError):
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
        return set(self.config.user_config.get('Sources', 'taxes_and_fees').split(','))

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
            except (KeyError):
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
                        except (KeyError):
                            snote = ''
                        sr[pay_month].setdefault('notes', set()).add(snote)

                        # % FI note
                        try:
                            pfi_note = savings[transfer][self.config.percent_fi_notes]
                        except (KeyError):
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
            except (KeyError):
                note = ''

            spending = pay - savings
            try:
                srate = fi.savings_rate(pay, spending)
            except (InvalidOperation):
                srate = Decimal(0)

            try:
                percent_fi = monthly_data[month]['percent_fi']
            except (KeyError):
                percent_fi = None

            try:
                pfi_note = monthly_data[month]['percent_fi_notes']
            except (KeyError):
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

    def plot_savings_rates(self, monthly_rates, embed=False):
        """
        Plots the monthly savings rates for a period of time.

        Args:
            monthly_rates: a list of tuples where the first item in each
            tupal is a python date object and the second item in each
            tuple is the savings rate for that month.

            embed, boolean defaults to False. Setting to true returns a
            plot for embedding in a web application.

        Returns:
            None
        """

        # Convenience variables
        graph_width = int(self.user.config.user_config.get('Graph', 'width'))
        graph_height = int(self.user.config.user_config.get('Graph', 'height'))
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
        output_file("savings-rates.html", title="Monthly Savings Rates")

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
        p.circle(x, y, size=6)
        inv = p.circle(
            x,
            y,
            size=15,
            fill_alpha=0.0,
            line_alpha=0.0,
        )

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
            # Set the width and the height
            p.height = graph_height
            p.width = graph_width
            p.sizing_mode = "scale_both"
            show(p)
        else:
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
        p.circle(
            x='percent_fi_x',
            y='percent_fi',
            size=6,
            color='#777777',
            source=non_empty_notes_source,
        )
        invisible_circle = p.circle(
            x='percent_fi_x',
            y='percent_fi',
            size=40,
            fill_alpha=0.0,
            line_alpha=0.0,
            source=non_empty_notes_source,
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
