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

import argparse
import json
import sys

from .db_config import DBConfigManager
from .savings_rate import Plot, SavingsRate, SRConfig


def get_initialized_db_manager():
    """
    Get a DBConfigManager instance with initialized database.
    Exits the program with error message if initialization fails.

    Returns:
        DBConfigManager: Initialized database manager
    """
    db_manager = DBConfigManager()
    if not db_manager.initialize_db():
        print("Failed to initialize database")
        sys.exit(1)
    return db_manager


def show_config():
    """
    Display current configuration from db.json.
    Console script entry point for sr-show-config command.
    """
    try:
        db_manager = get_initialized_db_manager()

        summary = db_manager.get_config_summary_lines()
        print("\nCurrent Configuration:")
        print("=" * 50)
        for line in summary:
            print(line)
    except Exception as e:
        print(f"Error reading configuration: {e}")
        sys.exit(1)


def validate_config():
    """
    Validate the current configuration in db.json.
    Console script entry point for sr-validate-config command.
    """
    try:
        db_manager = get_initialized_db_manager()

        is_valid, errors = db_manager.validate_config()

        if is_valid:
            print("✓ Configuration is valid")
        else:
            print("✗ Configuration has errors:")
            for error in errors:
                print(f"  - {error}")
            sys.exit(1)
    except Exception as e:
        print(f"Error validating configuration: {e}")
        sys.exit(1)


def update_setting():
    """
    Update a configuration setting in db.json.
    Console script entry point for sr-update-setting command.
    """
    parser = argparse.ArgumentParser(
        prog='sr-update-setting',
        description='Update a configuration setting in the MMM Savings Rate database',
    )
    parser.add_argument(
        'table', help='Table name (main_user_settings, enemy_settings, users)'
    )
    parser.add_argument('key', help='Setting key to update')
    parser.add_argument('value', help='New value for the setting')
    parser.add_argument(
        '--user-id', help='User ID (for enemy_settings or users table)', default='main'
    )

    # Parse all command line arguments (not just after a subcommand)
    args = parser.parse_args()

    try:
        db_manager = get_initialized_db_manager()

        # Convert value to appropriate type
        value = args.value
        if value.lower() in ['true', 'false']:
            value = value.lower() == 'true'
        elif value.startswith('[') and value.endswith(']'):
            # Handle list values
            value = json.loads(value)
        else:
            # Try to convert to number if possible
            try:
                if '.' in value:
                    value = float(value)
                else:
                    value = int(value)
            except ValueError:
                pass  # Keep as string

        db_manager.update_setting(args.table, args.key, value, args.user_id)
        print(f"✓ Updated {args.table}.{args.key} = {value}")

    except Exception as e:
        print(f"Error updating setting: {e}")
        sys.exit(1)


def run():
    """
    Run the application or handle configuration commands.
    """
    # Check for configuration management commands first
    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == 'show-config':
            show_config()
            return
        elif command == 'validate-config':
            validate_config()
            return
        elif command == 'update-setting':
            update_setting()
            return

    # Original savings rate plotting functionality
    parser = argparse.ArgumentParser(prog='savingsrates')
    parser.add_argument(
        '-u', '--user', type=int, help='User ID to analyze (default: 1)', default=1
    )
    parser.add_argument(
        '-o',
        '--output',
        type=str,
        help='Output path for HTML file (default: savings-rates.html)',
        default='savings-rates.html',
    )
    args = parser.parse_args()

    try:
        # Instantiate a savings rate config object
        config = SRConfig(user_id=args.user)

        # Instantiate a savings rate object for a user
        savings_rate = SavingsRate(config)
        monthly_rates = savings_rate.get_monthly_savings_rates()

        # Plot the user's savings rate
        user_plot = Plot(savings_rate)

    except Exception as e:
        print(f"Error: {e}")
        print(
            "\nTry running 'savingsrates validate-config' to check your configuration."
        )
        sys.exit(1)
    user_plot.plot_savings_rates(monthly_rates, output_path=args.output)
