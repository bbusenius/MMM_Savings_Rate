import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from db_config import DBConfigManager
from savings_rate import SRConfig


class TestDBConfigManager(unittest.TestCase):
    """
    Test the DBConfigManager class for TinyDB configuration management.
    """

    def setUp(self):
        """Set up test fixtures with temporary database file."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_db_path = Path(self.temp_dir) / "test_db.json"
        self.db_manager = DBConfigManager(str(self.test_db_path))

    def tearDown(self):
        """Clean up test fixtures."""
        # Close DBConfigManager to prevent ResourceWarnings
        if hasattr(self, 'db_manager') and self.db_manager:
            self.db_manager.close()

        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_initialize_db_creates_file(self):
        """Test that initialize_db creates the database file."""
        self.assertFalse(self.test_db_path.exists())
        result = self.db_manager.initialize_db()
        self.assertTrue(result)
        self.assertTrue(self.test_db_path.exists())

    def test_get_main_user_settings(self):
        """Test retrieving main user settings."""
        self.db_manager.initialize_db()
        settings = self.db_manager.get_main_user_settings()

        # Check that required fields exist
        required_fields = [
            'pay',
            'pay_date',
            'gross_income',
            'employer_match',
            'taxes_and_fees',
            'savings',
            'savings_date',
            'savings_accounts',
        ]
        for field in required_fields:
            self.assertIn(field, settings)

    def test_get_users(self):
        """Test retrieving users list."""
        self.db_manager.initialize_db()
        users = self.db_manager.get_users()

        self.assertIsInstance(users, list)
        self.assertGreater(len(users), 0)

        # Check first user structure
        user = users[0]
        self.assertIn('_id', user)
        self.assertIn('name', user)
        self.assertIn('config_ref', user)

    def test_validate_config_valid(self):
        """Test validation of valid configuration."""
        self.db_manager.initialize_db()
        is_valid, errors = self.db_manager.validate_config()

        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

    def test_update_setting(self):
        """Test updating a configuration setting."""
        self.db_manager.initialize_db()

        # Update a setting
        result = self.db_manager.update_setting('main_user_settings', 'goal', 75.0)
        self.assertTrue(result)

        # Verify the update
        settings = self.db_manager.get_main_user_settings()
        self.assertEqual(settings['goal'], 75.0)

    def test_update_setting_users_table(self):
        """Test updating a user in the users table."""
        # Create test data with multiple users
        test_data = {
            "main_user_settings": {
                "pay": "csv/income-example.csv",
                "pay_date": "Date",
                "gross_income": "Gross Pay",
                "employer_match": "Employer Match",
                "taxes_and_fees": ["OASDI", "Medicare"],
                "savings": "csv/savings-example.csv",
                "savings_date": "Date",
                "savings_accounts": ["Account1", "Account2"],
                "war": "on",
            },
            "users": [
                {"_id": 1, "name": "TestUser", "config_ref": "main_user_settings"},
                {
                    "_id": 2,
                    "name": "EnemyUser",
                    "config_ref": "enemy_settings",
                    "type": "enemy",
                },
            ],
            "enemy_settings": [],
        }

        with open(self.test_db_path, 'w') as f:
            json.dump(test_data, f, indent=2)

        # Update user by ID
        result = self.db_manager.update_setting(
            'users', 'name', 'UpdatedTestUser', user_id='1'
        )
        self.assertTrue(result)

        # Verify update by reading the file
        with open(self.test_db_path, 'r') as f:
            data = json.load(f)

        users = data['users']
        updated_user = next(user for user in users if user['_id'] == 1)
        self.assertEqual(updated_user['name'], 'UpdatedTestUser')

        # Update user by name
        result = self.db_manager.update_setting(
            'users', 'type', 'friendly', user_id='EnemyUser'
        )
        self.assertTrue(result)

        # Verify update
        with open(self.test_db_path, 'r') as f:
            data = json.load(f)

        users = data['users']
        updated_user = next(user for user in users if user['name'] == 'EnemyUser')
        self.assertEqual(updated_user['type'], 'friendly')

        # Test updating non-existent user
        result = self.db_manager.update_setting('users', 'name', 'Ghost', user_id='999')
        self.assertFalse(result)

    def test_update_setting_enemy_settings_table(self):
        """Test updating enemy settings table for war mode."""
        import json

        # Create test data with enemy settings
        test_data = {
            "main_user_settings": {
                "pay": "csv/income-example.csv",
                "pay_date": "Date",
                "gross_income": "Gross Pay",
                "employer_match": "Employer Match",
                "taxes_and_fees": ["OASDI", "Medicare"],
                "savings": "csv/savings-example.csv",
                "savings_date": "Date",
                "savings_accounts": ["Account1", "Account2"],
                "war": "on",
            },
            "users": [
                {"_id": 1, "name": "TestUser", "config_ref": "main_user_settings"}
            ],
            "enemy_settings": [
                {
                    "_id": 2,
                    "name": "Enemy1",
                    "pay": "csv/enemy1-income.csv",
                    "savings": "csv/enemy1-savings.csv",
                    "goal": 500000,
                },
                {
                    "_id": 3,
                    "name": "Enemy2",
                    "pay": "csv/enemy2-income.csv",
                    "savings": "csv/enemy2-savings.csv",
                    "goal": 750000,
                },
            ],
        }

        with open(self.test_db_path, 'w') as f:
            json.dump(test_data, f, indent=2)

        # Update enemy setting by ID
        result = self.db_manager.update_setting(
            'enemy_settings', 'goal', 600000, user_id='2'
        )
        self.assertTrue(result)

        # Verify update
        with open(self.test_db_path, 'r') as f:
            data = json.load(f)

        enemy_settings = data.get('enemy_settings', [])
        updated_enemy = next(enemy for enemy in enemy_settings if enemy['_id'] == 2)
        self.assertEqual(updated_enemy['goal'], 600000)

        # Update another enemy
        result = self.db_manager.update_setting(
            'enemy_settings', 'name', 'SuperEnemy', user_id='3'
        )
        self.assertTrue(result)

        # Verify update
        with open(self.test_db_path, 'r') as f:
            data = json.load(f)

        enemy_settings = data.get('enemy_settings', [])
        updated_enemy = next(enemy for enemy in enemy_settings if enemy['_id'] == 3)
        self.assertEqual(updated_enemy['name'], 'SuperEnemy')

        # Test updating non-existent enemy
        result = self.db_manager.update_setting(
            'enemy_settings', 'goal', 1000000, user_id='999'
        )
        self.assertFalse(result)

    def test_update_setting_unknown_table(self):
        """Test updating an unknown table returns False."""
        self.db_manager.initialize_db()

        result = self.db_manager.update_setting('unknown_table', 'key', 'value')
        self.assertFalse(result)


class TestSRConfigTinyDB(unittest.TestCase):
    """
    Test the SRConfig class with TinyDB configuration.
    """

    def setUp(self):
        """Set up test fixtures with temporary database."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_db_path = Path(self.temp_dir) / "test_db.json"

        # Create a test configuration
        test_config = {
            'main_user_settings': {
                'pay': '/test/income.xlsx',
                'pay_date': 'Date',
                'gross_income': 'Gross Pay',
                'employer_match': 'Employer Match',
                'taxes_and_fees': ['OASDI', 'Medicare', 'Federal Withholding'],
                'savings': '/test/savings.xlsx',
                'savings_date': 'Date',
                'savings_accounts': ['Vanguard Brokerage', 'Vanguard 403b'],
                'notes': 'Notes',
                'show_average': True,
                'war': 'off',
                'fred_url': 'https://api.stlouisfed.org/fred/series/observations?series_id=PSAVERT&file_type=json',
                'fred_api_key': 'test_api_key_12345',
                'goal': 70.0,
                'fi_number': 1000000,
                'total_balances': 'Total Balance',
                'percent_fi_notes': 'Total Balance Notes',
            },
            'users': [
                {"_id": 1, "name": "TestUser", "config_ref": "main_user_settings"}
            ],
            'enemy_settings': [],
        }

        with open(self.test_db_path, 'w') as f:
            json.dump(test_config, f, indent=2)

    def tearDown(self):
        """Clean up test fixtures."""
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_srconfig_initialization(self):
        """Test SRConfig initialization with TinyDB."""
        with SRConfig(test=True, test_file=str(self.test_db_path), user_id=1) as config:
            # Check that config loaded correctly
            self.assertEqual(config.user_id, 1)
            self.assertEqual(config.pay_source, "/test/income.xlsx")
            self.assertEqual(config.savings_source, "/test/savings.xlsx")
            self.assertEqual(config.goal, 70.0)
            self.assertEqual(config.fi_number, 1000000)

    def test_srconfig_load_user_config(self):
        """Test loading user configuration from TinyDB."""
        with SRConfig(test=True, test_file=str(self.test_db_path), user_id=1) as config:
            # Check that user config loaded correctly
            self.assertEqual(config.pay_source, "/test/income.xlsx")
            self.assertEqual(config.savings_source, "/test/savings.xlsx")
            self.assertEqual(config.pay_date, "Date")
            self.assertEqual(config.gross_income, "Gross Pay")
            self.assertEqual(config.employer_match, "Employer Match")
            self.assertEqual(config.savings_date, "Date")
            self.assertEqual(config.war_mode, False)
            self.assertEqual(config.goal, 70.0)
            self.assertEqual(config.fi_number, 1000000)
            self.assertEqual(config.show_average, True)

    def test_srconfig_invalid_user_id(self):
        """Test SRConfig with invalid user ID."""
        # Should raise an exception when invalid ID is provided
        with self.assertRaises(RuntimeError) as context:
            SRConfig(test=True, test_file=str(self.test_db_path), user_id=999)

        self.assertIn("User with ID 999 not found", str(context.exception))


if __name__ == '__main__':
    unittest.main()
