import ConfigParser
import csv
from dateutil import parser
import datetime
import mintapi
import keyring
import certifi
import sys
import getpass

# For debugging
from pprint import pprint 
import logging
import cProfile

class SavingsRate:
    """
    Class of getting and calculating a monthly savings rate
    based on information about monthly pay and spending.
    """
    
    def __init__(self):
        """
        Initialize the object with settings from the config file. 
        """
        
        # Set the date format to use throughout
        self.date_format = '%Y-%m-%d'

        # Required columns for spreadsheets
        self.required_income_columns = set(['Date'])
        self.required_savings_columns = set(['Date'])

        # Get the configurations
        self.config = ConfigParser.RawConfigParser()
        config = self.config.read('config.ini')

        # Set a log file
        self.log = self.config.get('Dev', 'logfile')
    
        # Ensure that a valid config file exists with the proper variables
        assert len(config) > 0, self.get_error_msg('no_config')
        
        # Get sources for pay and spending information
        try:
            self.pay_source = self.config.get('Sources', 'pay')
            self.savings_source = self.config.get('Sources', 'savings')
        except:
            print self.get_error_msg('missing_variable')

        # Ensure that proper configurations are set
        assert self.pay_source != '', self.get_error_msg('missing_variable')
        assert self.savings_source != '', self.get_error_msg('missing_variable')

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
        message = {'no_config' : 'No config.ini file was found. Please create a config file',
                   'missing_variable' : 'You are missing a required variable in the "Sources" section of config.ini',
                   'no_mint_username' : 'Please set your username in the "Mint" section of the config.ini',
                   'bad_spreadsheet_type' : 'You passed an improper spreadsheet type to test_columns()',
                   'required_savings_column' : 'You are missing a required column in ' +  self.savings_source + 
                        '. The following columns are required: ' + ', '.join(self.required_savings_columns) + '',
                   'required_income_column' : 'You are missing a required column in ' +  self.pay_source + 
                        '. The following columns are required: ' + ', '.join(self.required_income_columns) }

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
            retval = {} 
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
            retval = {} 
            reader = csv.DictReader(csvfile)
            for row in reader:
                # Make sure required columns are in the spreadsheet
                assert self.test_columns(set(row.keys()), 'savings') != set([]), \
                    self.get_error_msg('required_savings_column')
                dt_obj = parser.parse(row['Date'])
                date = dt_obj.strftime(self.date_format)
                retval[date] = row 
            self.income = retval


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
            print self.get_error_msg('no_mint_username')
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
            List of accounts used for tracking savings in mint. 
        """
        return set(self.config.get('Mint', 'savings_accounts').split(':'))


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


savings_rate = SavingsRate()
pprint(savings_rate.income)



