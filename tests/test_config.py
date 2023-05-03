import configparser
import unittest
from unittest import mock

from savings_rate import (
    REQUIRED_INI_ACCOUNT_OPTIONS,
    REQUIRED_INI_USER_OPTIONS,
    SavingsRate,
    SRConfig,
)


def return_bad_config():
    """
    Return a bad account-config.ini.
    """
    return SRConfig(
        'tests/test_config/',
        'config-test.ini',
        test=True,
        test_file='account-config-test-bad.ini',
    )


class TestSRConfigIni(unittest.TestCase):
    """
    Test the SRConfig class with .ini files.
    """

    def setUp(self):
        self.config = SRConfig('tests/test_config/', 'config-test.ini')
        self.sr = SavingsRate(self.config)
        self.config_missing = SRConfig(
            'tests/test_config/', 'config-missing-values.ini'
        )
        self.sr_missing_config = SavingsRate(self.config_missing)

    def test_load_account_config_without_ini(self):
        """
        Test the loading of account_config.ini.
        """
        # Load the config
        config = self.config

        # Unset the conf_dir path so the account_config.ini won't be found
        config.user_conf_dir = ''

        self.assertRaises(FileNotFoundError, config.load_account_config_from_ini)

    def test_load_account_config_without_section(self):
        """
        Load an account config without the required [Users] section.
        """
        config = self.config
        config.account_config.remove_section('Users')
        self.assertRaises(
            configparser.NoSectionError, config.account_config.get, 'Users', 'self'
        )

    def test_load_account_config_without_option(self):
        """
        Load a config option without the required "self" option.
        """
        config = self.config
        config.account_config.remove_option('Users', 'self')
        self.assertRaises(
            configparser.NoOptionError, config.account_config.get, 'Users', 'self'
        )

    def test_required_account_sections(self):
        """
        A missing required section in account-config.ini
        should throw an assertion error.
        """
        for section in REQUIRED_INI_ACCOUNT_OPTIONS:
            config = self.config
            config.account_config.remove_section(section)
            self.assertRaises(AssertionError, config.validate_account_ini)

    def test_required_account_options(self):
        """
        A missing required option in account-config.ini
        should throw an assertion error.
        """
        for section in REQUIRED_INI_ACCOUNT_OPTIONS:
            for option in REQUIRED_INI_ACCOUNT_OPTIONS[section]:
                config = self.config
                config.account_config.remove_option(section, option)
                self.assertRaises(AssertionError, config.validate_account_ini)

    def test_load_account_config_with_good_ini(self):
        """
        Load a good account-config.ini.
        """
        config = self.config

        self.assertEqual(
            len(config.user),
            3,
            'The "self" option in the [Users] section should have an id, name, and path to user config separated by commas.',
        )
        user_ids = set([])
        main_user_id = config.user[0]
        user_ids.add(main_user_id)

        if config.war_mode:
            for enemy in config.user_enemies:
                user_ids.add(enemy[0])
                self.assertEqual(
                    len(enemy),
                    3,
                    'If "war" is on. The "enemies" option must be se in the account-config.ini.',
                )
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
        config = SRConfig(
            'tests/test_config/',
            'config-test.ini',
            test=True,
            test_file='account-config-test-no-enemies.ini',
        )

        self.assertEqual(config.user_enemies, None)

    def test_required_user_sections(self):
        """
        A missing required section in config.ini
        should throw an assertion error.
        """
        for section in REQUIRED_INI_USER_OPTIONS:
            config = self.config
            config.user_config.remove_section(section)
            self.assertRaises(AssertionError, config.validate_user_ini)

    def test_required_user_options(self):
        """
        A missing required option in config.ini
        should throw an assertion error.
        """
        for section in REQUIRED_INI_USER_OPTIONS:
            for option in REQUIRED_INI_USER_OPTIONS[section]:
                config = self.config
                config.user_config.remove_option(section, option)
                self.assertRaises(AssertionError, config.validate_user_ini)

    def test_file_extension(self):
        val1 = self.sr.config.file_extension('test.txt')
        val2 = self.sr.config.file_extension('/this/is/just/a/test.csv')
        val3 = self.sr.config.file_extension('')

        self.assertEqual(val1, '.txt')
        self.assertEqual(val2, '.csv')
        self.assertEqual(val3, '')

    def test_load_notes_config(self):
        self.config.load_notes_config()
        self.assertEqual(self.sr.config.notes, 'My Notes')
        self.assertEqual(self.sr.config.percent_fi_notes, '% FI Notes')
        self.config_missing.load_notes_config()
        self.assertEqual(self.sr_missing_config.config.notes, '')
        self.assertEqual(self.sr_missing_config.config.percent_fi_notes, '')

    def test_goal_is_set_to_numeric_value(self):
        self.sr.config.load_goal_config()
        self.assertEqual(self.sr.config.goal, 70)

    def test_goal_is_set_to_false_when_no_option_is_provided(self):
        self.sr_missing_config.config.load_goal_config()
        self.assertEqual(self.sr_missing_config.config.goal, False)

    def test_goal_and_fi_number_when_non_numeric_value_is_provided(self):
        with mock.patch('builtins.print') as mock_print:
            config_bad = SRConfig('tests/test_config/', 'config-bad-values.ini')
            self.assertEqual(config_bad.goal, False)
            self.assertEqual(config_bad.fi_number, False)

            assert mock_print.call_count == 2

            # Can't use mock_print.assert_called_once_with because there are two
            # print statments
            mock_print.call_args_list[0][0][
                0
            ] == 'The value for \'goal\' should be numeric, e.g. 65.'
            mock_print.call_args_list[1][0][
                0
            ] == 'The value for \'fi_number\' should be numeric, e.g. 1000000.'

    def test_show_average_normally(self):
        self.sr.config.load_show_average_config()
        self.assertEqual(self.sr.config.show_average, True)

    def test_show_average_is_set_to_true_when_no_option_is_provided(self):
        self.sr_missing_config.config.load_show_average_config()
        self.assertEqual(self.sr_missing_config.config.show_average, True)

    def test_load_fi_number_config_is_set_to_numeric_value(self):
        self.sr.config.load_fi_number_config()
        self.assertEqual(self.sr.config.fi_number, 750000)

    def test_fi_number_is_set_to_false_when_no_option_is_provided(self):
        self.sr_missing_config.config.load_fi_number_config()
        self.assertEqual(self.sr_missing_config.config.fi_number, False)

    def test_load_total_balances_config(self):
        self.sr.config.load_total_balances_config()
        self.assertEqual(self.sr.config.total_balances, 'Balances')

    def test_load_total_balances_config_with_no_option_error(self):
        self.sr_missing_config.config.load_total_balances_config()
        self.assertEqual(self.sr_missing_config.config.total_balances, False)


class TestFREDConfig(unittest.TestCase):
    def setUp(self):
        self.config = SRConfig('tests/test_config/', 'config-test.ini')
        self.sr = SavingsRate(self.config)
        self.config_missing = SRConfig(
            'tests/test_config/', 'config-missing-values.ini'
        )
        self.sr_no_fred = SavingsRate(self.config_missing)

    def test_load_fred_config(self):
        self.sr.config.load_fred_url_config()
        self.sr.config.load_fred_api_key_config()
        has_fred = self.sr.config.has_fred()
        self.assertEqual(self.sr.config.fred_url, 'https://fred-test.com')
        self.assertEqual(self.sr.config.fred_api_key, 'test-api-key')
        self.assertEqual(has_fred, True)

    def test_load_fred_with_no_fred_settings(self):
        self.sr_no_fred.config.load_fred_url_config()
        self.sr_no_fred.config.load_fred_api_key_config()
        has_fred = self.sr_no_fred.config.has_fred()
        self.assertEqual(self.sr_no_fred.config.fred_url, '')
        self.assertEqual(self.sr_no_fred.config.fred_api_key, '')
        self.assertEqual(has_fred, False)
