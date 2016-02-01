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
from dateutil import parser
import datetime
import mintapi
import keyring
import certifi
import sys
import getpass
from collections import OrderedDict
from bokeh.plotting import figure, output_file, show
from bokeh.embed import components
from decimal import *
import simple_math as sm
from file_parsing import is_number_of_some_sort, are_numeric

# For debugging
from pprint import pprint 
import logging
import cProfile

REQUIRED_INI_ACCOUNT_OPTIONS = {'Users': ['self']}

REQUIRED_INI_USER_OPTIONS = {
    'Sources' : [
        'pay', 
        'pay_date', 
        'gross_income', 
        'employer_match', 
        'taxes_and_fees', 
        'savings', 
        'savings_accounts', 
        'savings_date', 
        'war'
    ],
    'Graph' : [
        'width', 
        'height'
    ]
}


class SRConfig:
    """
    Class for loading configurations to pass to the 
    savings rate object.

    Args:
        mode: a string representing a general source
        for data. Takes "ini" or "postgres".

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
    def __init__(self, mode='ini', user_conf_dir=None, user_conf=None, \
        user=None, enemies=None, test=False, test_file=None):

        self.mode = mode
        self.user_conf_dir = user_conf_dir
        self.user_ini = user_conf_dir + user_conf
        if self.mode == 'ini':
            self.is_test = test
            self.test_account_ini = test_file
            self.load_account_config() 
        elif self.mode == 'postgres':
            self.user = [user]
            self.user_enemies = [[]]

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
        if self.mode == 'ini':
            config = self.load_user_config_from_ini()
        elif self.mode == 'postgres':
            config = self.load_user_config_for_postgres()
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
            raise FileNotFoundError('The user config is an empty []. Create a user config file and make sure it\'s referenced in account-config.ini.')

        # Validate the configparser config object
        self.validate_user_ini()

        # Source of savings data (mint.com or .csv)
        self.savings_source = self.user_config.get('Sources', 'savings')

        # Source of income data
        self.pay_source = self.user_config.get('Sources', 'pay')

        # Set war mode
        self.war_mode = self.user_config.getboolean('Sources', 'war')

        # Savings and income sources
        self.pay_source = self.user_config.get('Sources', 'pay')
        self.savings_source = self.user_config.get('Sources', 'savings')

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
        self.required_income_columns = set([self.gross_income, self.employer_match, self.pay_date]).union(set(self.taxes_and_fees.split(',')))
        self.required_savings_columns = set([self.savings_date]).union(set(self.savings_accounts.split(',')))


    def validate_user_ini(self):
        """
        Minimum validation for the user 
        config.ini when running in 'ini' mode.
        """
        # Required section and options
        for section in REQUIRED_INI_USER_OPTIONS:
            assert self.user_config.has_section(section), \
                '[' + section + '] is a required section in the user config.ini.'
            for option in REQUIRED_INI_USER_OPTIONS[section]:
                assert self.user_config.has_option(section, option), \
                    'The "' + option + '" option is required in the [' + section + '] section of config.ini.'

        # Assumptions about the data
        assert are_numeric([self.user_config.get('Graph', 'width'), \
            self.user_config.get('Graph', 'height')]) == True, \
                '[Graph] width and height must contain numeric values.'

 
    def load_user_config_for_postgres(self):
        """
        Get user configurations from the database.
        """
        # Get user configurations
        self.user_config = configparser.RawConfigParser()
        config = self.user_config.read(self.user_ini)

        # Get database configurations
        self.db_host = self.user_config.get('PostgreSQL', 'host')
        self.db_name = self.user_config.get('PostgreSQL', 'dbname')
        self.db_user = self.user_config.get('PostgreSQL', 'user')
        self.db_password = self.user_config.get('PostgreSQL', 'password')

        # Set configurations
        self.pay_source = self.user_config.get('Sources', 'pay')
        self.savings_source = self.user_config.get('Sources', 'savings')
        self.gross_income = self.user_config.get('Sources', 'gross_income')
        self.employer_match = self.user_config.get('Sources', 'employer_match')
        self.taxes_and_fees = self.user_config.get('Sources', 'taxes_and_fees')
        self.savings_accounts = self.user_config.get('Sources', 'savings_accounts')
        self.war_mode = self.user_config.getboolean('Sources', 'war')
    

    def load_account_config_from_ini(self):
        """
        Get the configurations from an .ini file.
        Throw an exception if the file is lacking 
        required data.
        """
        # Load the ini
        self.account_config = configparser.RawConfigParser()
        if not self.is_test:
            account_config = self.account_config.read(self.user_conf_dir + 'account-config.ini')
        else:
            try:
                account_config = self.account_config.read(self.user_conf_dir + self.test_account_ini)
            except:
                raise RuntimeError('If test=True, a test .ini must be provided. You must provide a value for test_file.')

        # Raise an exception if the account_config comes back empty
        if account_config == []:
            raise FileNotFoundError('The account_config is an empty []. A file named, "account-config.ini" was not found. This file must exist.')

        # Validate the ini file.
        self.validate_account_ini()

        # Crosswalk data for the main player if it 
        # exists, otherwise throw an exception.
        self.user = self.account_config.get('Users', 'self').split(',')

        # If enemies isn't in the account-config.ini
        # set it to None.
        try:
            self.user_enemies = [enemy.split(',') for enemy in self.account_config.get('Users', 'enemies').split('|')]
        except(KeyError, configparser.NoOptionError):
            self.user_enemies = None

        # Set a log file (optional)
        self.log = self.account_config.get('Dev', 'logfile') if self.account_config.has_section('Dev') else None
        
        # Validate the data loaded from account-config.ini
        self.validate_loaded_account_data()


    def load_account_config_from_postgres(self):
        """
        Get configurations from a database.
        """
        pass


    def validate_account_ini(self):
        """
        Minimum validation for account-config.ini.
        """
        # Required sections
        assert self.account_config.has_section('Users'), \
            '[Users] is a required section in account-config.ini.'

        # Required options 
        assert self.account_config.has_option('Users', 'self'), \
            'The "self" option is required in the [Users] section of account-config.ini.'


    def validate_loaded_account_data(self):
        """
        Validate the data loaded from 
        account-config.ini.
        """
        assert len(self.user) == 3, \
            'The "self" option in the [Users] section should have an id, name, and path to user config separated by commas.'

        user_ids = set([])
        main_user_id = self.user[0]
        user_ids.add(main_user_id)

        if self.user_enemies:
            i = 1 # Self, already added
            for enemy in self.user_enemies:
                user_ids.add(enemy[0])
                assert len(enemy) == 3, 'The "enemies" option in account-config.ini is not set correctly.' 
                i += 1
            assert len(user_ids) ==  i, 'Every user ID must be unique.'


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

        # Don't require psycopg2 for desktop users
        if self.config.mode == 'postgres':
            import psycopg2

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
        
        required = {'income': self.config.required_income_columns,
                    'savings': self.config.required_savings_columns}

        if spreadsheet in required:
            val = row.issuperset(required[spreadsheet])
        else:
            msg = 'You passed an improper spreadsheet type to test_columns(). ' + \
                  'Possible values are "income" and "savings"'
            raise ValueError(msg)

        assert val == True, \
            'The ' + spreadsheet + ' spreadsheet is missing a column header. ' + \
            'following columns were configured: ' + str(required[spreadsheet]) + ' ' + \
            'but these column headings were found in the spreadsheet: ' + str(row)


    def connect_to_postgres_db(self):
        """
        Connects to a PostgreSQL database.

        Returns:
            A cursor object.
        """
        #Define our connection string
        conn_string = "host='%s' dbname='%s' user='%s' password='%s'" % (self.config.db_host, self.config.db_name, self.config.db_user, self.config.db_password)

        # Print a message
        print("Connecting to database...")
     
        # Get a connection, if a connect cannot be made an exception will be raised here
        conn = psycopg2.connect(conn_string)
     
        # conn.cursor will return a cursor object, you can use this cursor to perform queries
        return conn.cursor()


    def get_pay(self):
        """
        Loads payment data from a .csv fle.

        Args: 
            None

        Returns:
        """
        if self.config.mode == 'ini': 
            return self.load_pay_from_csv()
        elif self.config.mode == 'postgres':
            return self.load_pay_from_postgres()
        else:
            raise RuntimeError('Problem loading income information!')


    def load_pay_from_postgres(self):
        """
        Loads income data from a PostgreSQL database 
        and stores it in self.income.
        Expects number related columns to contain 
        python Decimal objects.

        Args: 
            None

        Returns:
            None
        """
        # Connect to the database and retrieve the needed fields
        cursor = self.connect_to_postgres_db()
        query = 'select date, gross_pay, employer_match, taxes_and_fees '\
            'from %s where user_id = %s' % (self.config.pay_source, self.config.user[0])
        cursor.execute(query)

        # Loop over the info and build a datastructure
        retval = OrderedDict()
        for date, gross_pay, employer_match, taxes_and_fees in cursor.fetchall():
            
            date_string = date.strftime(self.config.date_format)
            # Load the data, dictionary keys are entirely arbitrary
            retval[date_string] = {'Date': date, 
                                    self.config.gross_income : self.clean_num(gross_pay), 
                                    self.config.employer_match : self.clean_num(employer_match), 
                                    self.config.taxes_and_fees : self.clean_num(taxes_and_fees)} 

        self.income = retval


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
        except:
            pass 
        if number == None or number == '':
            retval = 0.0
        elif is_number_of_some_sort(number):
            retval = number
        else:
            raise TypeError('A numeric value was expected. The argument passed was non-numeric.')
        return retval


    def load_savings_from_postgres(self):
        """
        Loads savings data from a PostgreSQL database 
        and stores it in self.savings.
        Expects number related columns to contain 
        python Decimal objects.

        Args: 
            None

        Returns:
            None
        """
        # Connect to the database and retrieve the needed fields
        cursor = self.connect_to_postgres_db()
        query = 'select date, amount '\
            'from %s where user_id = %s' % (self.config.savings_source, self.config.user[0])
        cursor.execute(query)

        # Loop over the info and build a datastructure
        retval = OrderedDict()
        for date, amount in cursor.fetchall():
            date_string = date.strftime(self.config.date_format)
            # Load the data, dictionary keys are entirely arbitrary
            retval[date_string] = {'Date': date, self.config.savings_accounts : amount } 
        self.savings = retval
        

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
            for row in reader:
                # Make sure required columns are in the spreadsheet
                self.test_columns(set(row.keys()), 'income')
                dt_obj = parser.parse(row[self.config.pay_date])
                date = dt_obj.strftime(self.config.date_format)
                retval[date] = row
            self.income = retval


    def get_savings(self):
        """
        Get savings data from designated source.
        
        Args:
            None
        """
        if self.config.savings_source == 'mint':
            return self.load_savings_from_mint()
        elif self.config.mode == 'ini': 
            return self.load_savings_from_csv()
        elif self.config.mode == 'postgres':
            return self.load_savings_from_postgres()
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
            for row in reader:
                # Make sure required columns are in the spreadsheet
                self.test_columns(set(row.keys()), 'savings')
                
                dt_obj = parser.parse(row[self.config.savings_date])
                date = dt_obj.strftime(self.config.date_format)

                retval[date] = row 
            self.savings = retval


    def load_savings_from_mint(self):
        """
        Load spending data from mint.com.

        Args:
            None

        Returns:
            None, loads data from mint.com and attempts to save 
            user info. to the keyring if possible.
        """

        # Get username for mint.com from the config.ini
        username = self.config.get('Mint', 'username')

        # Get the password if available
        password = keyring.get_password(self.config.get('Sources', 'savings'), self.config.get('Mint', 'username'))

        # If the password isn't available get it and set it
        if not password:
            password = getpass.getpass("Enter your password for mint.com: ") 
            save = self.query_yes_no("Would you like to save the password to your system keyring?", None)
            
            # Store the password in the keyring if the user gives permission
            if save == True:
                keyring.set_password(self.config.get('Sources', 'spending'), username, password)
                
        # Instantiate a mint instance
        mint = mintapi.Mint(username, password)
        transactions = mint.get_transactions()

        # Accounts used to track spending
        savings_accounts = self.get_mint_savings_accounts()
        
        # DEBUG - complaints[is_noise & in_brooklyn][['Complaint Type', 'Borough', 'Created Date', 'Descriptor']][:10]
        logging.basicConfig(filename=self.log,level=logging.DEBUG)
        #logging.debug()        
 
        # Booleans for testing
        is_credit = transactions['transaction_type'] == 'credit'
        is_transfer = transactions['category'] == 'transfer'
        is_deposit = transactions['category'] == 'deposit'

        # TO DO - Learn how to do more processing here for efficiency instead of
        # crosswalking all the data below
        deposits = transactions[is_savings_account][['transaction_type', 'category', 'account_name', 'date', 'description', 'amount']] 
        #logging.debug(transactions[is_transfer])     

        # Crosswalk the data
        savings = self.crosswalk_mint_savings(deposits)


    def crosswalk_mint_savings(self, deposits):
        #logging.debug(deposits.iteritems())
        pass

    def get_mint_savings_accounts(self):
        """
        Get accounts used for tracking savings in mint.com.

        Args:
            None

        Returns:
            Set of accounts used for tracking savings in mint. 
        """
        return set(self.config.get('Mint', 'savings_accounts').split(':'))


    def get_taxes_from_csv(self):
        """
        Get the .csv column headers used for tracking taxes and fees 
        in the income related spreadsheet.

        Args:
            None

        Returns:
            Set of accounts used for tracking savings in mint. 
        """
        return set(self.config.user_config.get('Sources', 'taxes_and_fees').split(','))


    def query_yes_no(self, question, default="yes"):
        """
        Ask a yes/no question via raw_input() and return the answer.

        Args:
            question: a string to be presented to the user.
        
            default: string, the presumed answer if the user just hits <Enter>.
            It must be "yes" (the default), "no" or None (meaning an answer is 
            required of the user).

        Returns:
            boolean, the "answer" return value is True for "yes" or False for "no".
        
        Credit:
            I didn't write this one. Credit for this function goes to Trent Mick:
            https://code.activestate.com/recipes/577058/
        """

        valid = {"yes": True, "y": True, "ye": True,
                 "no": False, "n": False}
        if default is None:
            prompt = " [y/n] "
        elif default == "yes":
            prompt = " [Y/n] "
        elif default == "no":
            prompt = " [y/N] "
        else:
            raise ValueError("invalid default answer: '%s'" % default)

        while True:
            sys.stdout.write(question + prompt)
            choice = raw_input().lower()
            if default is not None and choice == '':
                return valid[default]
            elif choice in valid:
                return valid[choice]
            else:
                sys.stdout.write("Please respond with 'yes' or 'no' "
                                 "(or 'y' or 'n').\n")


    def get_monthly_data(self):
        """
        Crosswalk the data for income and spending into a structure
        representing one month time periods. Returns an OrderedDict.

        Args:
            None

        Returns:
            OrderedDict

        Example return data:

            OrderedDict({'2015-01' : {'income' : [Decimal(3500.0)],
                                      'employer_match' : [Decimal(120.0)],
                                      'taxes_and_fees' : [Decimal(450.0)],
                                      'savings' : [Decimal(1000.0)]},
                         '2015-02' : {'income' : [Decimal(3500.0)],
                                      'employer_match' : [Decimal(120.0)],
                                      'taxes_and_fees' : [Decimal(450.0)],
                                      'savings' : [Decimal(800.0)]}})
        """
        income = self.income.copy()
        savings = self.savings.copy()

        # For this data structure
        date_format = '%Y-%m'
        
        # Column headers used for tracking taxes and fees
        taxes = self.get_taxes_from_csv()

        # Dataset to return
        sr = OrderedDict()
        
        # Loop over income and savings
        for payout in income:
            # Structure the date
            pay_dt_obj = datetime.datetime.strptime(payout, self.config.date_format)
            pay_month = pay_dt_obj.strftime(date_format)

            # Get income data for inclusion, cells containing blank 
            # strings are converted to zeros.
            income_gross = 0 if income[payout][self.config.gross_income] == '' else income[payout][self.config.gross_income]
            income_match = 0 if income[payout][self.config.employer_match] == '' else income[payout][self.config.employer_match]
            income_taxes = [0 if income[payout][val] == '' else income[payout][val] for val in self.config.taxes_and_fees.split(',')]

            # Validate income spreadsheet data
            assert are_numeric([income_gross, income_match]) == True
            assert are_numeric(income_taxes) == True

            # If the data passes validation, convert it (strings to Decimal objects)
            gross = Decimal(income_gross) 
            employer_match = Decimal(income_match) 
            taxes = sum([Decimal(tax) for tax in income_taxes])

            #---Build the datastructure---

            # Set main dictionary key, encapsulte data by month 
            sr.setdefault(pay_month, {})

            # Set income related qualities for the month
            sr[pay_month].setdefault('income', []).append(gross)
            sr[pay_month].setdefault('employer_match', []).append(employer_match)
            sr[pay_month].setdefault('taxes_and_fees', []).append(taxes)

            if 'savings' not in sr[pay_month]:
                for transfer in savings:
                    tran_dt_obj = datetime.datetime.strptime(transfer, self.config.date_format)
                    tran_month = tran_dt_obj.strftime(date_format)

                    if tran_month == pay_month:

                        # Define savings data for inclusion
                        bank = [savings[transfer][val] for val in self.config.savings_accounts.split(',') if savings[transfer][val] != '']

                        # Validate savings spreadsheet data
                        assert are_numeric(bank) == True
                
                        # If the data passes validation, convert it (strings to Decimal objects)
                        money_in_the_bank = sum([Decimal(investment) for investment in bank])

                        # Set spending related qualities for the month
                        sr[pay_month].setdefault('savings', []).append(money_in_the_bank)

        return sr


    def get_monthly_savings_rates(self, test_data=False):
        """
        Calculates the monthly savings rates over 
        a period of time.

        Args:
            test_data: OrderedDict or boolean, for 
            passing in test data. Defaults to false. 

        Returns:
            A list of tuples where the first item 
            in each tupal is a python date object 
            and the second item in each tuple is 
            the savings rate for that month. 
        """
        if not test_data:
            monthly_data = self.get_monthly_data()
        else:
            monthly_data = test_data

        monthly_savings_rates = []
        for month in monthly_data:
            pay = sm.take_home_pay(sum(monthly_data[month]['income']), \
                sum(monthly_data[month]['employer_match']), \
                monthly_data[month]['taxes_and_fees'], 'decimal')
            savings = sum(monthly_data[month]['savings']) if 'savings' in monthly_data[month] else 0 
            spending = pay - savings
            srate = sm.savings_rate(pay, spending, 'decimal')
            date = datetime.datetime.strptime(month, '%Y-%m')
            monthly_savings_rates.append((date, srate))

        return monthly_savings_rates


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
        return sm.average([rate[1] for rate in monthly_rates], 'decimal')


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
        self.colors = ['#B30000', '#E34A33', '#8856a7', '#4D9221', \
                       '#404040', '#9E0142', '#0C2C84', '#810F7C']


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
        for data in monthly_rates:
            x.append(data[0])
            y.append(data[1])


        # Output to static HTML file
        output_file("savings-rates.html", title="Monthly Savings Rates")
        
        # Create a plot with a title and axis labels
        p = figure(title="Monthly Savings Rates", y_axis_label='% of take home pay', x_axis_type="datetime")

        p.below[0].formatter.formats = dict(years=['%Y'],
                                     months=['%b %Y'],
                                     days=['%b %d %Y'])

        # Add a line renderer with legend and line thickness
        p.line(x, y, legend="My savings rate", line_width=2)
        p.circle(x, y, size=6)

        # Plot the average monthly savings rate
        p.line(x, average_rate, legend="My average rate", line_color="#ff6600", line_dash="4 4")

        # Is PostgreSQL
        # Plot the savings rate of enemies if war_mode is on
        if self.user.config.war_mode == True:
            for war in self.user.config.user_enemies:
                # Enemy mode and configuration directory should always
                # be the same as user mode and configuration directory
                enemy_mode = self.user.config.mode
                enemy_conf_dir = self.user.config.user_conf_dir

                # Website mode
                if enemy_mode == 'postgres':
                    enemy_path = self.user.config.user_ini

                enemy_config = SRConfig(enemy_mode, enemy_conf_dir, war[2], war[0], [])
                enemy_savings_rate = SavingsRate(enemy_config)
                enemy_rates = enemy_savings_rate.get_monthly_savings_rates()
                enemy_x = []
                enemy_y = []

                for enemy_data in enemy_rates:
                    enemy_x.append(enemy_data[0])
                    enemy_y.append(enemy_data[1])

                # Plot the monthly savings rate for enemies
                p.line(enemy_x, enemy_y, legend=war[1] + '\'s savings rate', line_color=colors.pop(), line_width=2)

                # Reset the color palette if we run out of colors
                if len(colors) == 0:
                    colors = list(self.colors)

        p.legend.location = "top_left"

        # Show the results
        if embed == False:
            # Set the width and the height
            p.plot_height=graph_height 
            p.plot_width=graph_width 
            show(p)
        else:
            return components(p)
