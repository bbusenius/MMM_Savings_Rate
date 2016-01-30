import unittest
import configparser
from savings_rate import SRConfig, SavingsRate, Plot
from decimal import *
import sys

def return_bad_config():
    """
    Return a bad account-config.ini.
    """
    return SRConfig('ini', 'tests/test_config/', 'config-test.ini', \
            test=True, test_file='account-config-test-bad.ini')

class test_savings_rate_methods(unittest.TestCase):
    """
    Tests for individual methods.
    """
    def test_clean_num(self):
        config = SRConfig('ini', 'tests/test_config/', 'config-test.ini')
        sr = SavingsRate(config)

        val1 = sr.clean_num('')
        val2 = sr.clean_num('     ')
        val3 = sr.clean_num(None)
        val4 = sr.clean_num(4)
        val5 = sr.clean_num(4.4)
        val6 = sr.clean_num(Decimal(4.4))

        self.assertRaises(TypeError, sr.clean_num, 'Son of Mogh')
        self.assertRaises(TypeError, sr.clean_num, '4.4')
        self.assertEqual(val1, 0.0), 'An empty string should evaluate to 0.0. It evaluated to ' + str(val1)
        self.assertEqual(val2, 0.0), 'An empty string should evaluate to 0.0. It evaluated to ' + str(val2)
        self.assertEqual(val3, 0.0), 'None should evaluate to 0.0. It evaluated to ' + str(val3)
        self.assertEqual(val4, 4), '4 should evaluate to 4.4. It evaluated to ' + str(val4)
        self.assertEqual(val5, 4.4), '4.4 should evaluate to 4.4. It evaluated to ' + str(val5)
        self.assertEqual(val6, Decimal(4.4)), '4.4 should evaluate to Decimal(4.4). It evaluated to ' + str(val6)


class test_srconfig(unittest.TestCase):
    """
    Test the SRConfig class.
    """
    def test_load_account_config_without_ini(self):
        """
        Test the loading of account_config.ini.
        """
        # Load the config
        config = SRConfig('ini', 'tests/test_config/', 'config-test.ini')

        # Unset the conf_dir path so the account_config.ini won't be found
        config.user_conf_dir = ''

        self.assertRaises(FileNotFoundError, config.load_account_config_from_ini)


    def test_load_account_config_without_section(self):
        """
        Load an account config without the required [Users] section.
        """
        config = SRConfig('ini', 'tests/test_config/', 'config-test.ini')
        config.account_config.remove_section('Users')
        self.assertRaises(configparser.NoSectionError, config.account_config.get, 'Users', 'self')


    def test_load_account_config_without_option(self):
        """
        Load a config option without the required "self" option.
        """
        config = SRConfig('ini', 'tests/test_config/', 'config-test.ini')
        config.account_config.remove_option('Users', 'self')
        self.assertRaises(configparser.NoOptionError, config.account_config.get, 'Users', 'self')


    def test_load_account_config_with_good_ini(self):
        """
        Load a good account-config.ini.
        """
        config = SRConfig('ini', 'tests/test_config/', 'config-test.ini')    
        
        self.assertEqual(len(config.user), 3, \
            'The "self" option in the [Users] section should have an id, name, and path to user config separated by commas.')
        user_ids = set([])
        main_user_id = config.user[0] 
        user_ids.add(main_user_id)

        if config.war_mode:
            for enemy in config.user_enemies:
                user_ids.add(enemy[0])
                self.assertEqual(len(enemy), 3, \
                    'If "war" is on. The "enemies" option must be se in the account-config.ini.')
            self.assertEqual(len(user_ids), 3, 'Every user ID must be unique.')


    def test_load_account_config_with_bad_ini(self):
        """
        Load a poorly formed account-config.ini.
        """
        self.assertRaises(AssertionError, return_bad_config) 


    def test_load_account_config_without_enemies(self):
        """
        Loading an account_config.ini wout enemies
        shouldn't blow up.
        """
        config = SRConfig('ini', 'tests/test_config/', 'config-test.ini', \
            test=True, test_file='account-config-test-no-enemies.ini')

        self.assertEqual(config.user_enemies, None)


    def test_load_user_config(self):
        """
        Test load_user_config and load_user_config_from_ini.
        Are the proper configurations loaded? Check the data in
        tests/test_config/config-test.ini.
        """
        config = SRConfig('ini', 'tests/test_config/', 'config-test.ini')

        self.assertEqual(config.savings_source, 'csv/savings-example.csv', \
            'savings_source was incorrectly set in SRConfig.')
        self.assertEqual(config.pay_source, 'csv/income-example.csv', \
            'pay_source was incorrectly set in SRConfig.')
        self.assertEqual(config.war_mode, True, \
            'war_mode loaded incorrectly in SRConfig.')      
