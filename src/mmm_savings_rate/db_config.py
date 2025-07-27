"""
TinyDB-based configuration management for MMM Savings Rate.

This module provides configuration management using a single JSON database
managed by TinyDB for storing user, account, and enemy configurations.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from tinydb import TinyDB

# Default configuration values
DEFAULT_MAIN_USER_SETTINGS = {
    "pay": "csv/income-example.xlsx",
    "pay_date": "Date",
    "gross_income": "Gross Pay",
    "employer_match": "Employer Match",
    "taxes_and_fees": ["OASDI", "Medicare", "Federal Withholding", "State Tax"],
    "savings": "csv/savings-example.xlsx",
    "savings_date": "Date",
    "savings_accounts": ["Scottrade", "Vanguard 403b", "Vanguard Roth"],
    "notes": "",
    "show_average": True,
    "war": "off",
    "fred_url": "https://api.stlouisfed.org/fred/series/observations?series_id=PSAVERT&file_type=json",
    "fred_api_key": "",
    "goal": None,
    "fi_number": None,
    "total_balances": "",
    "percent_fi_notes": "",
}

DEFAULT_USERS = [{"_id": 1, "name": "User", "config_ref": "main_user_settings"}]

# Required fields for validation
REQUIRED_MAIN_USER_FIELDS = [
    'pay',
    'pay_date',
    'gross_income',
    'employer_match',
    'taxes_and_fees',
    'savings',
    'savings_accounts',
    'savings_date',
    'war',
]

REQUIRED_USER_FIELDS = ['_id', 'name', 'config_ref']


class DBConfigManager:
    """
    Manages TinyDB-based configuration for MMM Savings Rate.

    Handles loading, validation, and management of configuration data
    stored in a single JSON file using TinyDB.
    """

    def __init__(self, db_path=None):
        """
        Initialize the database configuration manager.

        Args:
            db_path (str, optional): Path to the database file.
            Defaults to ~/.mmm_savings_rate/db.json
        """
        if db_path:
            self.db_path = Path(db_path)
        else:
            # Default path
            home_dir = Path.home()
            config_dir = home_dir / '.mmm_savings_rate'
            config_dir.mkdir(exist_ok=True)
            self.db_path = config_dir / 'db.json'

        self.db = None
        self.logger = None
        self._setup_logging()

    def _setup_logging(self):
        """
        Set up logging for database operations.
        """
        # Create logs directory if it doesn't exist
        log_dir = self.db_path.parent
        log_dir.mkdir(exist_ok=True)

        # Set up logger
        self.logger = logging.getLogger('db_config')
        self.logger.setLevel(logging.ERROR)

        # Create file handler
        log_file = log_dir / 'error.log'
        self.file_handler = logging.FileHandler(log_file)
        self.file_handler.setLevel(logging.ERROR)

        # Create console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.ERROR)

        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        # Add handlers to logger
        if not self.logger.handlers:
            self.logger.addHandler(self.file_handler)
            self.logger.addHandler(console_handler)

    def _get_db(self):
        """
        Get a TinyDB instance. Creates a new connection each time to avoid ResourceWarnings.
        """
        return TinyDB(str(self.db_path))

    def close(self):
        """
        Close logging handlers to free resources and prevent ResourceWarnings.
        """
        # Close logging handlers to prevent ResourceWarnings
        if hasattr(self, 'logger') and self.logger:
            for handler in self.logger.handlers[:]:
                handler.close()
                self.logger.removeHandler(handler)

        # Close file handler specifically if it exists
        if hasattr(self, 'file_handler') and self.file_handler:
            self.file_handler.close()

    def __enter__(self):
        """
        Context manager entry. Enables usage with 'with' statements.

        Example:
            with DBConfigManager() as db_manager:
                settings = db_manager.get_main_user_settings()
            # Logging handlers automatically closed here
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Context manager exit - automatically calls close() to clean up logging handlers.
        This prevents ResourceWarnings from unclosed file handlers.
        """
        self.close()

    def log_config_error(self, error_type: str, message: str, details: Dict = None):
        """Log configuration errors with context."""
        error_msg = f"[{error_type}] {message}"
        if details:
            error_msg += f" Details: {details}"
        self.logger.error(error_msg)

    def log_config_warning(self, warning_type: str, message: str):
        """Log configuration warnings."""
        warning_msg = f"[{warning_type}] {message}"
        self.logger.warning(warning_msg)

    def _ensure_db_initialized(self) -> None:
        """Ensure database is initialized, raising RuntimeError if it fails."""
        if not self.db:
            if not self.initialize_db():
                raise RuntimeError("Failed to initialize database")

    def initialize_db(self) -> bool:
        """
        Initialize the database with default values if it doesn't exist or is empty.

        Returns:
            bool: True if initialization was successful, False otherwise.
        """
        try:
            # Check if file exists and is valid JSON
            if self.db_path.exists():
                try:
                    with open(self.db_path, 'r') as f:
                        data = json.load(f)

                    # Check if database has required tables
                    if self._has_required_structure(data):
                        # Database is valid, no need to keep connection open
                        return True

                except json.JSONDecodeError as e:
                    error_msg = f"Invalid JSON in {self.db_path}: {e}"
                    self.logger.error(error_msg)
                    print(f"Error: {error_msg}")
                    return False

            # Initialize with default data
            self._create_default_db()
            return True

        except Exception as e:
            error_msg = f"Failed to initialize database: {e}"
            self.logger.error(error_msg)
            print(f"Error: {error_msg}")
            return False

    def _has_required_structure(self, data: Dict) -> bool:
        """Check if the JSON data has the required TinyDB structure."""
        required_tables = ['main_user_settings', 'enemy_settings', 'users']
        return all(table in data for table in required_tables)

    def _create_default_db(self):
        """Create a new database file with default configuration."""
        default_data = {
            'main_user_settings': DEFAULT_MAIN_USER_SETTINGS,
            'enemy_settings': [],
            'users': DEFAULT_USERS,
        }

        # Ensure directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Write default data
        with open(self.db_path, 'w') as f:
            json.dump(default_data, f, indent=2)

    def get_main_user_settings(self) -> Dict[str, Any]:
        """
        Get the main user settings.

        Returns:
            Dict containing main user configuration settings.
        """
        if not self.initialize_db():
            raise RuntimeError("Failed to initialize database")

        # TinyDB stores the main_user_settings as a single document
        # We need to read it directly from the JSON structure
        with open(self.db_path, 'r') as f:
            data = json.load(f)

        return data.get('main_user_settings', DEFAULT_MAIN_USER_SETTINGS)

    def get_enemy_settings(self, enemy_id: int) -> Optional[Dict[str, Any]]:
        """
        Get enemy settings by ID.

        Args:
            enemy_id: The unique ID of the enemy.

        Returns:
            Dict containing enemy configuration settings, or None if not found.
        """
        self._ensure_db_initialized()

        with open(self.db_path, 'r') as f:
            data = json.load(f)

        enemy_settings = data.get('enemy_settings', [])
        for enemy in enemy_settings:
            if enemy.get('_id') == enemy_id:
                return enemy

        return None

    def get_users(self) -> List[Dict[str, Any]]:
        """
        Get all users.

        Returns:
            List of user dictionaries.
        """
        self._ensure_db_initialized()

        with open(self.db_path, 'r') as f:
            data = json.load(f)

        return data.get('users', DEFAULT_USERS)

    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Get user information by ID.

        Args:
            user_id: The user ID to look up.

        Returns:
            Dict containing user information, or None if not found.
        """
        users = self.get_users()
        for user in users:
            if user.get('_id') == user_id:
                return user
        return None

    def get_user_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get user information by name.

        Args:
            name: The user name to look up.

        Returns:
            Dict containing user information, or None if not found.
        """
        users = self.get_users()
        for user in users:
            if user.get('name') == name:
                return user
        return None

    def update_main_user_setting(self, key: str, value: Any) -> bool:
        """
        Update a main user setting.

        Args:
            key: The setting key to update.
            value: The new value for the setting.

        Returns:
            bool: True if update was successful, False otherwise.
        """
        try:
            with open(self.db_path, 'r') as f:
                data = json.load(f)

            if 'main_user_settings' not in data:
                data['main_user_settings'] = DEFAULT_MAIN_USER_SETTINGS.copy()

            # Handle special parsing for list fields
            if key in ['taxes_and_fees', 'savings_accounts'] and isinstance(value, str):
                # Parse comma-separated string into list
                value = [item.strip() for item in value.split(',') if item.strip()]

            data['main_user_settings'][key] = value

            with open(self.db_path, 'w') as f:
                json.dump(data, f, indent=2)

            return True

        except Exception as e:
            error_msg = f"Failed to update setting {key}: {e}"
            self.logger.error(error_msg)
            print(f"Error: {error_msg}")
            return False

    def update_setting(
        self, table: str, key: str, value: Any, user_id: str = 'main'
    ) -> bool:
        """
        Update a setting in the specified table.

        Args:
            table: The table name (main_user_settings, enemy_settings, users)
            key: The setting key to update
            value: The new value for the setting
            user_id: User ID for enemy_settings or users table

        Returns:
            bool: True if update was successful, False otherwise
        """
        try:
            if table == 'main_user_settings':
                return self.update_main_user_setting(key, value)
            elif table == 'users':
                # Update user information
                with open(self.db_path, 'r') as f:
                    data = json.load(f)

                users = data.get('users', [])
                for user in users:
                    if (
                        str(user.get('_id')) == str(user_id)
                        or user.get('name') == user_id
                    ):
                        user[key] = value
                        break
                else:
                    self.log_config_error('UPDATE_ERROR', f'User {user_id} not found')
                    return False

                with open(self.db_path, 'w') as f:
                    json.dump(data, f, indent=2)
                return True

            elif table == 'enemy_settings':
                # Update enemy settings
                with open(self.db_path, 'r') as f:
                    data = json.load(f)

                enemy_settings = data.get('enemy_settings', [])
                for enemy in enemy_settings:
                    if str(enemy.get('_id')) == str(user_id):
                        enemy[key] = value
                        break
                else:
                    self.log_config_error('UPDATE_ERROR', f'Enemy {user_id} not found')
                    return False

                with open(self.db_path, 'w') as f:
                    json.dump(data, f, indent=2)
                return True
            else:
                self.log_config_error('UPDATE_ERROR', f'Unknown table: {table}')
                return False

        except Exception as e:
            self.log_config_error(
                'UPDATE_ERROR', f'Failed to update {table}.{key}', {'error': str(e)}
            )
            return False

    def validate_config(self) -> tuple[bool, List[str]]:
        """
        Validate the configuration data.

        Returns:
            Tuple of (is_valid, error_messages). is_valid is True if no errors.
        """
        errors = []

        try:
            if not self.db_path.exists():
                errors.append(f"Database file {self.db_path} does not exist")
                return len(errors) == 0, errors

            with open(self.db_path, 'r') as f:
                data = json.load(f)

        except json.JSONDecodeError as e:
            errors.append(f"Invalid JSON in {self.db_path}: {e}")
            return len(errors) == 0, errors
        except Exception as e:
            errors.append(f"Failed to read database file: {e}")
            return len(errors) == 0, errors

        # Validate structure
        if not self._has_required_structure(data):
            errors.append(
                "Database missing required tables: main_user_settings, enemy_settings, users"
            )
            return len(errors) == 0, errors

        # Validate main user settings
        main_settings = data.get('main_user_settings', {})
        for field in REQUIRED_MAIN_USER_FIELDS:
            if field not in main_settings:
                errors.append(f"Missing required field in main_user_settings: {field}")

        # Validate users
        users = data.get('users', [])
        if not users:
            errors.append("No users defined")
        else:
            user_ids = set()
            for user in users:
                for field in REQUIRED_USER_FIELDS:
                    if field not in user:
                        errors.append(f"Missing required field in user: {field}")

                user_id = user.get('_id')
                if user_id in user_ids:
                    errors.append(f"Duplicate user ID: {user_id}")
                user_ids.add(user_id)

        # Validate enemy settings
        enemy_settings = data.get('enemy_settings', [])
        enemy_ids = set()
        for enemy in enemy_settings:
            enemy_id = enemy.get('_id')
            if enemy_id in enemy_ids:
                errors.append(f"Duplicate enemy ID: {enemy_id}")
            enemy_ids.add(enemy_id)

            for field in REQUIRED_MAIN_USER_FIELDS:
                if field not in enemy:
                    errors.append(
                        f"Missing required field in enemy {enemy_id}: {field}"
                    )

        return len(errors) == 0, errors

    def get_config_summary(self) -> Dict[str, Any]:
        """
        Get a formatted summary of the configuration.

        Returns:
            Dict containing configuration summary.
        """
        try:
            with open(self.db_path, 'r') as f:
                data = json.load(f)

            summary = {
                'main_user_settings': data.get('main_user_settings', {}),
                'users': data.get('users', []),
                'enemy_count': len(data.get('enemy_settings', [])),
                'enemies_configured': len(data.get('enemy_settings', [])) > 0,
            }

            return summary

        except Exception as e:
            error_msg = f"Failed to get config summary: {e}"
            self.logger.error(error_msg)
            return {'error': error_msg}

    def get_config_summary_lines(self) -> List[str]:
        """
        Get a formatted summary of the configuration as lines for CLI display.

        Returns:
            List of formatted strings for display.
        """
        try:
            with open(self.db_path, 'r') as f:
                data = json.load(f)

            lines = []

            # Main user settings
            main_settings = data.get('main_user_settings', {})
            lines.append("Main User Settings:")
            for key, value in main_settings.items():
                if isinstance(value, list):
                    value_str = (
                        ', '.join(str(v) for v in value) if value else '(empty list)'
                    )
                else:
                    value_str = str(value) if value is not None else '(not set)'
                lines.append(f"  {key}: {value_str}")

            lines.append("")

            # Users
            users = data.get('users', [])
            lines.append(f"Users ({len(users)}):")
            for user in users:
                lines.append(
                    f"  ID: {user.get('_id')}, Name: {user.get('name')}, Config: {user.get('config_ref')}"
                )

            lines.append("")

            # Enemy settings
            enemies = data.get('enemy_settings', [])
            lines.append(f"Enemy Settings ({len(enemies)}):")
            if enemies:
                for i, enemy in enumerate(enemies):
                    lines.append(f"  Enemy {i + 1}: {enemy}")
            else:
                lines.append("  (no enemies configured)")

            return lines

        except Exception as e:
            error_msg = f"Failed to get config summary: {e}"
            self.logger.error(error_msg)
            return [f"Error: {error_msg}"]
