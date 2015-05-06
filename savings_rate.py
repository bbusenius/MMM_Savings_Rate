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
from bokeh.plotting import figure, output_file, show, VBox
#from simple_math import take_home_pay, savings_rate
import simple_math as sm
from file_parsing import is_numeric, are_numeric

# For debugging
from pprint import pprint 
import logging
import cProfile

class SavingsRate:
    """
    Class for getting and calculating a monthly savings rate
    based on information about monthly pay and spending.
    """
    
    def __init__(self, user_config='config/config.ini' ):
        """
        Initialize the object with settings from the config file. 
        """

        # ------------------------------------------
        # === Set config files ===
        # ------------------------------------------

        # Get the application configurations
        self.account_config = configparser.RawConfigParser()
        account_config = self.account_config.read('config/account-config.ini')
            
        # Get the user configurations
        self.config = configparser.RawConfigParser()
        config = self.config.read(user_config)


        # ------------------------------------------
        # === Make sure config files exist ===
        # ------------------------------------------

        assert account_config != [], 'You are missing the main configuration for the application. \
            Make sure you have an account-config.ini.'
        assert config != [], 'No config.ini file was found. Please create a config file.'


        # ------------------------------------------
        # === Validate config files ===
        # ------------------------------------------

        try:
            self.pay_source = self.config.get('Sources', 'pay')
            self.savings_source = self.config.get('Sources', 'savings')
        except:
            print(self.get_error_msg('missing_variable'))

        # Ensure that proper configurations are set
        assert self.pay_source != '', self.get_error_msg('missing_variable')
        assert self.savings_source != '', self.get_error_msg('missing_variable')


        # ------------------------------------------
        # === Relevant configurations from the account config ===
        # ------------------------------------------
        self.user = self.account_config.get('Users', 'self').split(',')
        self.user_enemies = [enemy.split(',') for enemy in self.account_config.get('Users', 'enemies').split('|')]
        # Set a log file
        self.log = self.account_config.get('Dev', 'logfile') if self.account_config.has_section('Dev') else None


        # ------------------------------------------
        # === Relevant configurations from the user config  ===
        # ------------------------------------------

        # Source of savings data (mint.com or .csv)
        self.savings_source = self.config.get('Sources', 'savings')
        # Set war mode
        self.war_mode = self.config.getboolean('Sources', 'war')
    

        # ------------------------------------------
        # === Spreadsheet validation ===
        # ------------------------------------------

        # Required columns for spreadsheets
        self.required_income_columns = set(['Date'])
        self.required_savings_columns = set(['Date'])

        # Spreadsheet columns that should have numeric data
        self.numeric_columns = set([self.config.get('Sources', 'gross_income'), \
            self.config.get('Sources', 'employer_match'), \
            ', '.join(self.config.get('Sources', 'taxes_and_fees').split(',', )), \
            ', '.join(self.config.get('Sources', 'savings_accounts').split(',', ))])

        # Spreadsheet columns we care about, these are just column names
        self.gross_income = self.config.get('Sources', 'gross_income')
        self.employer_match = self.config.get('Sources', 'employer_match')
        self.taxes_and_fees = self.config.get('Sources', 'taxes_and_fees')
        self.savings_accounts = self.config.get('Sources', 'savings_accounts')


        # ------------------------------------------
        # === Finish loading data ===
        # ------------------------------------------

        # Set the date format to use
        self.date_format = '%Y-%m-%d'

        # Load income and savings information
        self.get_pay()
        self.get_savings() 


    def get_error_msg(self, error_type):
        """
        Return an error message for a given condition.

        Args:
            error_type: string, the type of error to retrieve.

        Returns:
            String, error message
        """

        # Error messages
        message = {'missing_variable' : 'You are missing a required variable in the "Sources" section of config.ini',
                   'no_mint_username' : 'Please set your username in the "Mint" section of the config.ini',
                   'bad_spreadsheet_type' : 'You passed an improper spreadsheet type to test_columns()',
                   'required_savings_column' : 'You are missing a required column in ' +  self.savings_source + 
                        '. The following columns are required: ' + ', '.join(self.required_savings_columns) + '',
                   'required_income_column' : 'You are missing a required column in ' +  self.pay_source + 
                        '. The following columns are required: ' + ', '.join(self.required_income_columns),
                   'non_numeric_data' : 'Some of your spreadsheet data is not numeric. The following spreadsheet columns should be numeric: ' + ', '.join(self.numeric_columns)}

        return message[error_type]

    
    def test_columns(self, row, string):
        """
        Make sure the required columns are present for different 
        types of spreadsheets.

        Args:
            row: a set representing column headers from a spreadsheet.

            string: the type of spreadsheet to validate. Possible
            values are "income" or "spending".
        """
        if string == 'income':
            val = self.required_income_columns.intersection(row)
        elif string == 'savings':
            val = self.required_savings_columns.intersection(row)
        else:
            sys.exit(self.get_error_msg('bad_spreadsheet_type'))
        return val


    def get_pay(self):
        """
        Loads payment data from a .csv fle.

        Args: 
            None

        Returns:
        """
        pay_type = {'csv' : self.load_pay_from_csv()} 
   
        if self.is_csv(self.pay_source): 
            return pay_type['csv']
        else:
            return None 


    def is_csv(self, name):
        """
        Checks to see if the reference to a filename
        is a reference to a .csv file. Does NOT test
        if the file actually is a .csv file.

        Args:
            name, string

        Returns:
            boolean
        """
        return name[-4:] == '.csv'


    def load_pay_from_csv(self):
        """
        Loads a paystub from a .csv file.
        
        Args: 
            None

        Returns:
            None
        """
        with open(self.pay_source) as csvfile:
            retval = OrderedDict() 
            reader = csv.DictReader(csvfile)
            for row in reader:
                # Make sure required columns are in the spreadsheet
                assert self.test_columns(set(row.keys()), 'income') != set([]), \
                    self.get_error_msg('required_income_column')

                dt_obj = parser.parse(row['Date'])
                date = dt_obj.strftime(self.date_format)
                retval[date] = row 
            self.income = retval


    def get_savings(self):
        """
        Get savings data from designated source.
        
        Args:
            None
        """
        if self.savings_source == 'mint':
            return self.load_savings_from_mint()
        elif self.is_csv(self.savings_source): 
            return self.load_savings_from_csv()


    def load_savings_from_csv(self):
        """
        Loads savings data from a .csv file.
        
        Args: 
            None

        Returns:
            None
        """
        with open(self.savings_source) as csvfile:
            retval = OrderedDict() 
            reader = csv.DictReader(csvfile)
            for row in reader:
                # Make sure required columns are in the spreadsheet
                assert self.test_columns(set(row.keys()), 'savings') != set([]), \
                    self.get_error_msg('required_savings_column')
                dt_obj = parser.parse(row['Date'])
                date = dt_obj.strftime(self.date_format)

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
        try:
            username = self.config.get('Mint', 'username')
        except:
            print(self.get_error_msg('no_mint_username'))
        assert username != '', self.get_error_msg('no_mint_username')

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
        return set(self.config.get('Sources', 'taxes_and_fees').split(','))


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

        Example data structure:
 
             sr  = {'2015-01-29' : {'income' : [3500.0],
                                    'employer_match' : [120.0],
                                    'taxes_and_fees' : [450.0],
                                    'savings' : [1000.0]},
                    '2015-02-27' : {'income' : [3500.0],
                                    'employer_match' : [120.0],
                                    'taxes_and_fees' : [450.0],
                                    'savings' : [800.0]}}
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
            pay_dt_obj = datetime.datetime.strptime(payout, self.date_format)
            pay_month = pay_dt_obj.strftime(date_format)

            # Get income data for inclusion, cells containing blank 
            # strings are converted to zeros.
            income_gross = 0 if income[payout][self.gross_income] == '' else income[payout][self.gross_income]
            income_match = 0 if income[payout][self.employer_match] == '' else income[payout][self.employer_match]
            income_taxes = [0 if income[payout][val] == '' else income[payout][val] for val in self.taxes_and_fees.split(',')]

            # Validate income spreadsheet data
            assert are_numeric([income_gross, income_match]) == True, self.get_error_msg('non_numeric_data')
            assert are_numeric(income_taxes) == True, self.get_error_msg('non_numeric_data')

            # If the data passes validation, convert it (strings to floats)
            gross = float(income_gross) 
            employer_match = float(income_match) 
            taxes = sum([float(tax) for tax in income_taxes])

            #---Build the datastructure---

            # Set main dictionary key, encapsulte data by month 
            sr.setdefault(pay_month, {})

            # Set income related qualities for the month
            sr[pay_month].setdefault('income', []).append(gross)
            sr[pay_month].setdefault('employer_match', []).append(employer_match)
            sr[pay_month].setdefault('taxes_and_fees', []).append(taxes)

            if 'savings' not in sr[pay_month]:
                for transfer in savings:
                    tran_dt_obj = datetime.datetime.strptime(transfer, self.date_format)
                    tran_month = tran_dt_obj.strftime(date_format)

                    if tran_month == pay_month:

                        # Define savings data for inclusion
                        bank = [savings[transfer][val] for val in self.savings_accounts.split(',') if savings[transfer][val] != '']

                        # Validate savings spreadsheet data
                        assert are_numeric(bank) == True, self.get_error_msg('non_numeric_data')
                
                        # If the data passes validation, convert it (strings to floats)
                        money_in_the_bank = sum([float(investment) for investment in bank])

                        # Set spending related qualities for the month
                        sr[pay_month].setdefault('savings', []).append(money_in_the_bank)

        return sr


    def get_monthly_savings_rates(self):
        """
        Calculates the monthly savings rates over a period of time.

        Args:
            None

        Returns:
            A list of tuples where the first item in each tupal is a python
            date object and the second item in each tuple is the savings 
            rate for that month. 
        """
        
        monthly_data = self.get_monthly_data()
        monthly_savings_rates = []
        for month in monthly_data:
            pay = sm.take_home_pay(sum(monthly_data[month]['income']), sum(monthly_data[month]['employer_match']), monthly_data[month]['taxes_and_fees'])
            savings = sum(monthly_data[month]['savings']) if 'savings' in monthly_data[month] else 0 
            spending = pay - savings
            srate = sm.savings_rate(pay, spending)
            date = datetime.datetime.strptime(month, '%Y-%m')
            monthly_savings_rates.append((date, srate))

        return monthly_savings_rates


    def average_monthly_savings_rates(self, monthly_rates):
        """
        Calculates the average monthly savings rate for a period of months.

        Args:
            monthly_rates: a list of tuples where the first item in each tupal is a python
            date object and the second item in each tuple is the savings 
            rate for that month.

        Returns:
            float
        """
        return sm.average([rate[1] for rate in monthly_rates])


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


    def plot_savings_rates(self, monthly_rates):
        """
        Plots the monthly savings rates for a period of time.

        Args:
            monthly_rates: a list of tuples where the first item in each 
            tupal is a python date object and the second item in each 
            tuple is the savings rate for that month.

        Returns:
            None 
        """

        # Convenience variables
        graph_width = int(self.user.config.get('Graph', 'width'))
        graph_height = int(self.user.config.get('Graph', 'height'))
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
        p = figure(title="Monthly Savings Rates", y_axis_label='% of take home pay', x_axis_type="datetime", \
            plot_width=graph_width, plot_height=graph_height)

        p.below[0].formatter.formats = dict(years=['%Y'],
                                     months=['%b %Y'],
                                     days=['%b %d %Y'])

        # Add a line renderer with legend and line thickness
        p.line(x, y, legend="My savings rate", line_width=2)
        p.circle(x, y, size=6)

        # Plot the average monthly savings rate
        p.line(x, average_rate, legend="My average rate", line_color="#ff6600", line_dash="4 4")

        # Plot the savings rate of enemies if war_mode is on
        if self.user.war_mode == True:
            for war in self.user.user_enemies:
                enemy_savings_rate = SavingsRate(war[1])
                enemy_rates = enemy_savings_rate.get_monthly_savings_rates()
                enemy_x = []
                enemy_y = []

                for enemy_data in enemy_rates:
                    enemy_x.append(enemy_data[0])
                    enemy_y.append(enemy_data[1])

                # Plot the monthly savings rate for enemies
                p.line(enemy_x, enemy_y, legend=war[0] + '\'s savings rate', line_color=colors.pop(), line_width=2)

                # Reset the color palette if we run out of colors
                if len(colors) == 0:
                    colors = list(self.colors)

        p.legend.orientation = "top_left"
        # Show the results
        show(p)
    


    
# Instantiate a savings rate object for a user
savings_rate = SavingsRate()
monthly_rates = savings_rate.get_monthly_savings_rates()

# Plot the user's savings rate
user_plot = Plot(savings_rate)
user_plot.plot_savings_rates(monthly_rates)
