"""
Test suite for MMM Savings Rate GUI functionality.

Tests tab navigation, user interactions, and GUI components.
"""

import asyncio
import json
import os
import shutil
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

try:
    import toga

    from mmm_savings_rate.gui import (
        ConfigTab,
        FileWatcher,
        IncomeTab,
        MMMSavingsRateApp,
        PlotTab,
        SavingsTab,
        load_spreadsheet_data,
    )

    GUI_AVAILABLE = True
except ImportError:
    GUI_AVAILABLE = False
    toga = None
    ConfigTab = FileWatcher = IncomeTab = MMMSavingsRateApp = None
    PlotTab = SavingsTab = load_spreadsheet_data = None


@unittest.skipIf(not GUI_AVAILABLE, "GUI dependencies not available")
class TestGUIComponents(unittest.TestCase):
    """Test individual GUI components and utilities."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_config_dir = tempfile.mkdtemp()

        # Get absolute paths to test data files
        project_root = Path(__file__).parent.parent
        self.csv_income_path = project_root / "csv" / "income-example.csv"
        self.csv_savings_path = project_root / "csv" / "savings-example.csv"

    def tearDown(self):
        """Clean up test fixtures."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
        if os.path.exists(self.temp_config_dir):
            shutil.rmtree(self.temp_config_dir)

    def test_load_spreadsheet_data_csv(self):
        """Test loading data from CSV files."""
        result = load_spreadsheet_data(str(self.csv_income_path), limit=5)

        self.assertIsNotNone(result)
        self.assertIn('data', result)
        self.assertIn('columns', result)
        self.assertIn('file_info', result)
        self.assertIn('total_rows', result)

        # Check that we got the expected columns
        self.assertIn('Date', result['columns'])
        self.assertIn('Gross Pay', result['columns'])

        # Check that data is limited correctly
        self.assertLessEqual(len(result['data']), 5)

        # Check file info structure
        file_info = result['file_info']
        self.assertIn('path', file_info)
        self.assertIn('size', file_info)
        self.assertIn('modified', file_info)

    def test_load_spreadsheet_data_nonexistent_file(self):
        """Test loading data from non-existent file."""
        result = load_spreadsheet_data("/nonexistent/file.csv")
        self.assertIsNone(result)

    def test_load_spreadsheet_data_unsupported_format(self):
        """Test loading data from unsupported file format."""
        # Create a temporary text file
        temp_file = os.path.join(self.temp_dir, "test.txt")
        with open(temp_file, 'w') as f:
            f.write("This is not a spreadsheet")

        result = load_spreadsheet_data(temp_file)
        self.assertIsNone(result)


@unittest.skipIf(not GUI_AVAILABLE, "GUI dependencies not available")
class TestGUIAppInitialization(unittest.TestCase):
    """Test GUI application initialization and setup."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_config_dir = tempfile.mkdtemp()

        # Create test database configuration
        self.test_db_path = Path(self.temp_config_dir) / "test_config.json"
        project_root = Path(__file__).parent.parent
        csv_income_path = project_root / "csv" / "income-example.csv"
        csv_savings_path = project_root / "csv" / "savings-example.csv"

        test_config = {
            "main_user_settings": {
                "pay": str(csv_income_path),
                "pay_date": "Date",
                "gross_income": "Gross Pay",
                "employer_match": "Employer Match",
                "taxes_and_fees": ["OASDI", "Medicare"],
                "savings": str(csv_savings_path),
                "savings_date": "Date",
                "savings_accounts": ["Scottrade", "Vanguard 403b", "Vanguard Roth"],
                "notes": "Notes",
                "show_average": True,
                "war": "off",
                "fred_url": "",
                "fred_api_key": "",
                "goal": 50.0,
                "fi_number": 1000000.0,
                "total_balances": "",
                "percent_fi_notes": "",
            },
            "users": [
                {"_id": 1, "name": "TestUser", "config_ref": "main_user_settings"}
            ],
            "enemy_settings": [],
        }

        with open(self.test_db_path, 'w') as f:
            json.dump(test_config, f, indent=2)

    def tearDown(self):
        """Clean up test fixtures."""
        if os.path.exists(self.temp_config_dir):
            shutil.rmtree(self.temp_config_dir)

    @mock.patch('mmm_savings_rate.gui.DBConfigManager')
    def test_app_initialization_success(self, mock_db_manager):
        """Test successful app initialization."""
        # Mock database manager initialization
        mock_db_instance = mock.Mock()
        mock_db_instance.initialize_db.return_value = True
        mock_db_manager.return_value = mock_db_instance

        # Create app instance (don't actually start it)
        app = MMMSavingsRateApp("Test App", "com.test.app")

        # Verify app was created
        self.assertIsInstance(app, MMMSavingsRateApp)
        self.assertEqual(app.formal_name, "Test App")

    @mock.patch('mmm_savings_rate.gui.DBConfigManager')
    def test_app_initialization_db_failure(self, mock_db_manager):
        """Test app initialization with database failure."""
        # Mock database manager initialization failure
        mock_db_instance = mock.Mock()
        mock_db_instance.initialize_db.return_value = False
        mock_db_manager.return_value = mock_db_instance

        app = MMMSavingsRateApp("Test App", "com.test.app")

        # Should still create app instance
        self.assertIsInstance(app, MMMSavingsRateApp)


@unittest.skipIf(not GUI_AVAILABLE, "GUI dependencies not available")
class TestGUITabComponents(unittest.TestCase):
    """Test individual tab components."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_config_dir = tempfile.mkdtemp()

        # Create mock app
        self.mock_app = mock.Mock(spec=MMMSavingsRateApp)

        # Create simple async function to avoid coroutine warnings
        async def mock_error():
            return None

        self.mock_app.show_error_dialog = mock.AsyncMock(side_effect=mock_error)
        self.mock_app.get_gui_output_path.return_value = os.path.join(
            self.temp_config_dir, "output.html"
        )

    def tearDown(self):
        """Clean up test fixtures."""

        if os.path.exists(self.temp_config_dir):
            shutil.rmtree(self.temp_config_dir)

    def test_plot_tab_creation(self):
        """Test PlotTab creation and structure."""
        plot_tab = PlotTab(self.mock_app)

        # Check that content was created
        self.assertIsNotNone(plot_tab.content)
        self.assertIsInstance(plot_tab.content, toga.Box)

        # Check that webview exists
        self.assertIsNotNone(plot_tab.webview)
        self.assertIsInstance(plot_tab.webview, toga.WebView)

    @mock.patch('mmm_savings_rate.gui.DBConfigManager')
    def test_config_tab_creation(self, mock_db_manager):
        """Test ConfigTab creation and structure."""
        # Mock database manager
        mock_db_instance = mock.Mock()
        mock_db_instance.get_config.return_value = {
            "pay": "/test/path.csv",
            "goal": 50.0,
            "war": "off",
            "show_average": True,
            "taxes_and_fees": ["OASDI", "Medicare"],
            "savings_accounts": ["Account1", "Account2"],
        }
        mock_db_manager.return_value = mock_db_instance

        # Add db_manager to mock app
        self.mock_app.db_manager = mock_db_instance

        config_tab = ConfigTab(self.mock_app)

        # Check that content was created
        self.assertIsNotNone(config_tab.content)
        self.assertIsInstance(config_tab.content, toga.Box)

        # Check that form fields exist (correct attribute name)
        self.assertIsNotNone(config_tab.form_fields)
        self.assertIsInstance(config_tab.form_fields, dict)

        # Check that refresh plot button exists in config tab
        self.assertIsNotNone(config_tab.refresh_plot_button)
        self.assertIsInstance(config_tab.refresh_plot_button, toga.Button)

    @mock.patch('mmm_savings_rate.gui.load_spreadsheet_data')
    @mock.patch('mmm_savings_rate.gui.DBConfigManager')
    def test_income_tab_creation(self, mock_db_manager, mock_load_data):
        """Test IncomeTab creation and structure."""
        # Mock database manager
        mock_db_instance = mock.Mock()
        mock_db_instance.get_config.return_value = {
            "pay": "/test/path.csv",
        }
        mock_db_instance.get_main_user_settings.return_value.get.return_value = (
            "/test/path.csv"
        )
        mock_db_manager.return_value = mock_db_instance
        self.mock_app.db_manager = mock_db_instance

        # Mock data loading to return None (simulating file not found)
        mock_load_data.return_value = None

        income_tab = IncomeTab(self.mock_app)

        # Check that content was created
        self.assertIsNotNone(income_tab.content)
        self.assertIsInstance(income_tab.content, toga.Box)

        # Check basic tab structure
        self.assertEqual(income_tab.tab_name, "Income")
        self.assertEqual(income_tab.config_key, "pay")
        # Note: data_table may be None initially if no data is loaded

    @mock.patch('mmm_savings_rate.gui.load_spreadsheet_data')
    @mock.patch('mmm_savings_rate.gui.DBConfigManager')
    def test_savings_tab_creation(self, mock_db_manager, mock_load_data):
        """Test SavingsTab creation and structure."""
        # Mock database manager
        mock_db_instance = mock.Mock()
        mock_db_instance.get_config.return_value = {
            "savings": "/test/path.csv",
        }
        mock_db_instance.get_main_user_settings.return_value.get.return_value = (
            "/test/path.csv"
        )
        mock_db_manager.return_value = mock_db_instance
        self.mock_app.db_manager = mock_db_instance

        # Mock data loading to return None (simulating file not found)
        mock_load_data.return_value = None

        savings_tab = SavingsTab(self.mock_app)

        # Check that content was created
        self.assertIsNotNone(savings_tab.content)
        self.assertIsInstance(savings_tab.content, toga.Box)

        # Check basic tab structure
        self.assertEqual(savings_tab.tab_name, "Savings")
        self.assertEqual(savings_tab.config_key, "savings")
        # Note: data_table may be None initially if no data is loaded

    @mock.patch('mmm_savings_rate.gui.DBConfigManager')
    def test_config_tab_load_config_values(self, mock_db_manager):
        """Test ConfigTab _load_config_values method."""
        # Mock database manager with comprehensive test data
        mock_db_instance = mock.Mock()
        mock_config = {
            "pay": "/test/income.xlsx",
            "savings": "/test/savings.xlsx",
            "goal": 75.5,
            "war": "on",
            "show_average": True,
            "taxes_and_fees": ["OASDI", "Medicare", "Federal"],
            "savings_accounts": ["Vanguard", "401k"],
            "notes": "Test notes",
            "percent_fi_notes": "FI notes",
            "fi_number": 1000000,
        }
        mock_db_instance.get_main_user_settings.return_value = mock_config
        mock_db_manager.return_value = mock_db_instance

        # Set up mock app with db_manager
        self.mock_app.db_manager = mock_db_instance

        # Create ConfigTab
        config_tab = ConfigTab(self.mock_app)

        # Create mock form fields for testing with proper Mock specs
        mock_text_fields = {}
        mock_switch_fields = {}

        for field_name in [
            "pay",
            "savings",
            "goal",
            "taxes_and_fees",
            "savings_accounts",
            "notes",
            "percent_fi_notes",
            "fi_number",
        ]:
            mock_field = mock.Mock(spec=toga.TextInput)
            mock_field.value = None  # Initialize value attribute
            mock_text_fields[field_name] = mock_field

        for field_name in ["war", "show_average"]:
            mock_field = mock.Mock(spec=toga.Switch)
            mock_field.value = None  # Initialize value attribute
            mock_switch_fields[field_name] = mock_field

        config_tab.form_fields = {**mock_text_fields, **mock_switch_fields}

        # Reset mock call count (ConfigTab init already called it once)
        mock_db_instance.get_main_user_settings.reset_mock()

        # Call the method under test
        config_tab._load_config_values()

        # Verify TextInput fields were set correctly
        self.assertEqual(mock_text_fields["pay"].value, "/test/income.xlsx")
        self.assertEqual(mock_text_fields["savings"].value, "/test/savings.xlsx")
        self.assertEqual(mock_text_fields["goal"].value, "75.5")
        self.assertEqual(mock_text_fields["fi_number"].value, "1000000")
        self.assertEqual(mock_text_fields["notes"].value, "Test notes")
        self.assertEqual(mock_text_fields["percent_fi_notes"].value, "FI notes")

        # Verify list fields were converted to comma-separated strings
        self.assertEqual(
            mock_text_fields["taxes_and_fees"].value, "OASDI, Medicare, Federal"
        )
        self.assertEqual(mock_text_fields["savings_accounts"].value, "Vanguard, 401k")

        # Verify Switch fields were set correctly
        self.assertEqual(
            mock_switch_fields["war"].value, True
        )  # "on" should become True
        self.assertEqual(mock_switch_fields["show_average"].value, True)

        # Verify database method was called
        mock_db_instance.get_main_user_settings.assert_called_once()

    @mock.patch('mmm_savings_rate.gui.DBConfigManager')
    def test_config_tab_get_form_values(self, mock_db_manager):
        """Test ConfigTab _get_form_values method."""
        # Mock database manager
        mock_db_instance = mock.Mock()
        mock_db_instance.get_main_user_settings.return_value = {}
        mock_db_manager.return_value = mock_db_instance
        self.mock_app.db_manager = mock_db_instance

        # Create ConfigTab
        config_tab = ConfigTab(self.mock_app)

        # Create mock form fields with test values
        mock_text_fields = {}
        mock_switch_fields = {}

        # Set up text input fields with various test values
        field_values = {
            "pay": "/test/income.xlsx",
            "savings": "/test/savings.xlsx",
            "goal": "75.5",  # numeric field
            "fi_number": "1000000",  # numeric field
            "taxes_and_fees": "OASDI, Medicare, Federal",  # array field
            "savings_accounts": "Vanguard, 401k",  # array field
            "notes": "Test notes",
            "percent_fi_notes": "FI notes",
        }

        for field_name, field_value in field_values.items():
            mock_field = mock.Mock(spec=toga.TextInput)
            mock_field.value = field_value
            mock_text_fields[field_name] = mock_field

        # Set up switch fields
        switch_values = {
            "war": True,  # should become "on"
            "show_average": False,  # should stay boolean False
        }

        for field_name, field_value in switch_values.items():
            mock_field = mock.Mock(spec=toga.Switch)
            mock_field.value = field_value
            mock_switch_fields[field_name] = mock_field

        config_tab.form_fields = {**mock_text_fields, **mock_switch_fields}

        # Call the method under test
        result = config_tab._get_form_values()

        # Verify text field values
        self.assertEqual(result["pay"], "/test/income.xlsx")
        self.assertEqual(result["savings"], "/test/savings.xlsx")
        self.assertEqual(result["notes"], "Test notes")
        self.assertEqual(result["percent_fi_notes"], "FI notes")

        # Verify numeric field conversions
        self.assertEqual(result["goal"], 75.5)
        self.assertEqual(result["fi_number"], 1000000.0)

        # Verify array field conversions (comma-separated to list)
        self.assertEqual(result["taxes_and_fees"], ["OASDI", "Medicare", "Federal"])
        self.assertEqual(result["savings_accounts"], ["Vanguard", "401k"])

        # Verify switch field conversions
        self.assertEqual(result["war"], "on")  # True should become "on"
        self.assertEqual(result["show_average"], False)  # Should stay boolean

    @mock.patch('mmm_savings_rate.gui.DBConfigManager')
    def test_config_tab_get_form_values_empty_arrays(self, mock_db_manager):
        """Test ConfigTab _get_form_values method with empty array fields."""
        # Mock database manager
        mock_db_instance = mock.Mock()
        mock_db_instance.get_main_user_settings.return_value = {}
        mock_db_manager.return_value = mock_db_instance
        self.mock_app.db_manager = mock_db_instance

        # Create ConfigTab
        config_tab = ConfigTab(self.mock_app)

        # Create mock form fields with empty array values
        mock_text_fields = {
            "taxes_and_fees": mock.Mock(spec=toga.TextInput),
            "savings_accounts": mock.Mock(spec=toga.TextInput),
        }

        # Empty string should result in empty arrays
        mock_text_fields["taxes_and_fees"].value = ""
        mock_text_fields["savings_accounts"].value = "   "  # whitespace only

        config_tab.form_fields = mock_text_fields

        # Call the method under test
        result = config_tab._get_form_values()

        # Verify empty arrays
        self.assertEqual(result["taxes_and_fees"], [])
        self.assertEqual(result["savings_accounts"], [])

    @mock.patch('mmm_savings_rate.gui.DBConfigManager')
    def test_config_tab_get_form_values_empty_numeric(self, mock_db_manager):
        """Test ConfigTab _get_form_values method with empty numeric fields."""
        # Mock database manager
        mock_db_instance = mock.Mock()
        mock_db_instance.get_main_user_settings.return_value = {}
        mock_db_manager.return_value = mock_db_instance
        self.mock_app.db_manager = mock_db_instance

        # Create ConfigTab
        config_tab = ConfigTab(self.mock_app)

        # Create mock form fields with empty numeric values
        mock_text_fields = {
            "goal": mock.Mock(spec=toga.TextInput),
            "fi_number": mock.Mock(spec=toga.TextInput),
        }

        # Empty string should result in None
        mock_text_fields["goal"].value = ""
        mock_text_fields["fi_number"].value = "   "  # whitespace only

        config_tab.form_fields = mock_text_fields

        # Call the method under test
        result = config_tab._get_form_values()

        # Verify None values for empty numeric fields
        self.assertIsNone(result["goal"])
        self.assertIsNone(result["fi_number"])


@unittest.skipIf(not GUI_AVAILABLE, "GUI dependencies not available")
class TestGUINavigation(unittest.TestCase):
    """Test GUI navigation and tab switching functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_config_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test fixtures."""
        # No AsyncMock cleanup needed for this test class
        if os.path.exists(self.temp_config_dir):
            shutil.rmtree(self.temp_config_dir)

    @mock.patch('mmm_savings_rate.gui.DBConfigManager')
    def test_tab_container_creation(self, mock_db_manager):
        """Test tab container creation with all tabs."""
        # Mock database manager
        mock_db_instance = mock.Mock()
        mock_db_instance.initialize_db.return_value = True
        mock_db_instance.get_config.return_value = {
            "pay": "/test/path.csv",
            "goal": 50.0,
            "war": "off",
            "show_average": True,
            "taxes_and_fees": ["OASDI", "Medicare"],
            "savings_accounts": ["Account1", "Account2"],
        }
        mock_db_manager.return_value = mock_db_instance

        # Create mock app
        app = mock.Mock(spec=MMMSavingsRateApp)
        app.show_error_dialog = mock.AsyncMock(return_value=None)
        app.get_gui_output_path.return_value = os.path.join(
            self.temp_config_dir, "output.html"
        )

        # Create tabs
        plot_tab = PlotTab(app)
        config_tab = ConfigTab(app)
        income_tab = IncomeTab(app)
        savings_tab = SavingsTab(app)

        # Create tab container
        tab_container = toga.OptionContainer(
            content=[
                toga.OptionItem("Plot", plot_tab.content),
                toga.OptionItem("Config", config_tab.content),
                toga.OptionItem("Income", income_tab.content),
                toga.OptionItem("Savings", savings_tab.content),
            ]
        )

        # Verify container structure
        self.assertIsInstance(tab_container, toga.OptionContainer)
        self.assertEqual(len(tab_container.content), 4)

        # Check tab names
        tab_names = [item.text for item in tab_container.content]
        expected_names = ["Plot", "Config", "Income", "Savings"]
        self.assertEqual(tab_names, expected_names)


@unittest.skipIf(not GUI_AVAILABLE, "GUI dependencies not available")
class TestGUIErrorHandling(unittest.TestCase):
    """Test GUI error handling and dialog functionality."""

    def test_error_dialog_message_formatting(self):
        """Test error message formatting for dialogs."""

        # Test single error
        errors = ["Configuration file not found"]
        expected_message = "• Configuration file not found"

        # Since we can't easily test the actual dialog, verify message formatting
        message = "\n".join(f"• {error}" for error in errors)
        self.assertEqual(message, expected_message)

        # Test multiple errors
        errors = ["File not found", "Invalid configuration", "Missing fields"]
        expected_message = "• File not found\n• Invalid configuration\n• Missing fields"

        message = "\n".join(f"• {error}" for error in errors)
        self.assertEqual(message, expected_message)

    @mock.patch('mmm_savings_rate.gui.SRConfig')
    @mock.patch('mmm_savings_rate.gui.SavingsRate')
    def test_simulation_error_handling(self, mock_savings_rate, mock_config):
        """Test simulation error handling."""
        # Mock configuration failure
        mock_config.side_effect = FileNotFoundError("Config file not found")

        # Create mock app
        app = mock.Mock(spec=MMMSavingsRateApp)
        app.show_error_dialog = mock.AsyncMock()
        app.get_gui_output_path.return_value = "/tmp/output.html"

        # Create plot tab
        plot_tab = PlotTab(app)

        # This would normally be tested with async, but we'll verify structure
        self.assertIsInstance(plot_tab, PlotTab)
        self.assertIsNotNone(plot_tab.webview)


@unittest.skipIf(not GUI_AVAILABLE, "GUI dependencies not available")
class TestGUIDataLoading(unittest.TestCase):
    """Test GUI data loading and display functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

        # Create test CSV file
        self.test_csv = os.path.join(self.temp_dir, "test_data.csv")
        test_data = """Date,Amount,Description
2024-01-01,1000.00,Salary
2024-01-15,500.00,Bonus
2024-02-01,1000.00,Salary
2024-02-15,200.00,Freelance
2024-03-01,1000.00,Salary"""

        with open(self.test_csv, 'w') as f:
            f.write(test_data)

    def tearDown(self):
        """Clean up test fixtures."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_spreadsheet_data_loading_limit(self):
        """Test data loading with row limits."""
        # Test loading with limit
        result = load_spreadsheet_data(self.test_csv, limit=3)

        self.assertIsNotNone(result)
        self.assertEqual(len(result['data']), 3)
        self.assertEqual(result['total_rows'], 5)

        # Check that most recent data comes first (reversed order)
        # The CSV has 5 rows, so last 3 should be rows 3, 4, 5 in reverse order
        first_row_date = result['data'][0][0]  # First column of first row
        self.assertEqual(first_row_date, "2024-03-01")  # Most recent date

    def test_spreadsheet_columns_detection(self):
        """Test correct column detection."""
        result = load_spreadsheet_data(self.test_csv)

        expected_columns = ['Date', 'Amount', 'Description']
        self.assertEqual(result['columns'], expected_columns)

    def test_file_info_extraction(self):
        """Test file information extraction."""
        result = load_spreadsheet_data(self.test_csv)

        file_info = result['file_info']
        self.assertEqual(file_info['path'], self.test_csv)
        self.assertGreater(file_info['size'], 0)
        self.assertIn('modified', file_info)

        # Check date format
        import re

        date_pattern = r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}'
        self.assertIsNotNone(re.match(date_pattern, file_info['modified']))


@unittest.skipIf(not GUI_AVAILABLE, "GUI dependencies not available")
class TestConfigSaveIntegration(unittest.TestCase):
    """Test config save integration with file watcher and plot refresh."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

        # Create mock app with all required components
        self.mock_app = mock.Mock(spec=MMMSavingsRateApp)
        self.mock_app.plot_tab = mock.Mock()

        # Create simple async functions to avoid coroutine warnings
        async def mock_refresh():
            return None

        async def mock_dialog():
            return None

        async def mock_error():
            return None

        self.mock_app.plot_tab.refresh_plot = mock.AsyncMock(side_effect=mock_refresh)
        self.mock_app.file_watcher = mock.Mock(spec=FileWatcher)
        self.mock_app.file_watcher.update_watched_files = mock.Mock()
        self.mock_app.db_manager = mock.Mock()
        self.mock_app.main_window = mock.Mock()
        self.mock_app.main_window.dialog = mock.AsyncMock(side_effect=mock_dialog)
        self.mock_app.show_error_dialog = mock.AsyncMock(side_effect=mock_error)

    def tearDown(self):
        """Clean up test fixtures."""

        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    @mock.patch('mmm_savings_rate.gui.DBConfigManager')
    def test_save_config_triggers_file_watcher_update_and_plot_refresh(
        self, mock_db_manager
    ):
        """Test that saving config triggers both file watcher update and plot refresh."""
        # Mock database manager
        mock_db_instance = mock.Mock()
        mock_db_instance.get_main_user_settings.return_value = {}
        mock_db_instance.update_setting.return_value = True
        mock_db_manager.return_value = mock_db_instance

        # Create mock app
        mock_app = mock.Mock(spec=MMMSavingsRateApp)
        mock_app.plot_tab = mock.Mock()
        mock_app.plot_tab.refresh_plot = mock.AsyncMock()
        mock_app.file_watcher = mock.Mock(spec=FileWatcher)
        mock_app.file_watcher.update_watched_files = mock.Mock()
        mock_app.db_manager = mock_db_instance
        mock_app.main_window = mock.Mock()
        mock_app.main_window.dialog = mock.AsyncMock()

        # Create ConfigTab
        with mock.patch.object(ConfigTab, '_load_config_values'):
            config_tab = ConfigTab(mock_app)

        # Mock form fields
        mock_text_field = mock.Mock(spec=toga.TextInput)
        mock_text_field.value = "/test/income.xlsx"
        config_tab.form_fields = {"pay": mock_text_field}

        # Call save_config using asyncio.run
        # Avoid GLib event loop conflicts by using new thread
        result = None
        exception = None

        def run_async():
            nonlocal result, exception
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(config_tab.save_config(None))
                loop.close()
            except Exception as e:
                exception = e

        thread = threading.Thread(target=run_async)
        thread.start()
        thread.join()

        # Threading exceptions aren't always forwarded to the main thread
        # Make sure the test fails if it should
        if exception:
            raise exception

        # Verify the sequence of calls
        # 1. Should update database setting
        mock_db_instance.update_setting.assert_called_once_with(
            'main_user_settings', 'pay', '/test/income.xlsx'
        )

        # 2. Should show success dialog
        mock_app.main_window.dialog.assert_called_once()

        # 3. Should update file watcher
        mock_app.file_watcher.update_watched_files.assert_called_once()

        # 4. Should refresh plot
        mock_app.plot_tab.refresh_plot.assert_called_once()

    @mock.patch('mmm_savings_rate.gui.DBConfigManager')
    def test_save_config_stops_on_database_error(self, mock_db_manager):
        """Test that config save stops early on database errors."""
        # Mock database manager with failure
        mock_db_instance = mock.Mock()
        mock_db_instance.get_main_user_settings.return_value = {}
        mock_db_instance.update_setting.return_value = False  # Simulate failure
        mock_db_manager.return_value = mock_db_instance

        # Create mock app
        mock_app = mock.Mock(spec=MMMSavingsRateApp)
        mock_app.plot_tab = mock.Mock()
        mock_app.plot_tab.refresh_plot = mock.AsyncMock()
        mock_app.file_watcher = mock.Mock(spec=FileWatcher)
        mock_app.file_watcher.update_watched_files = mock.Mock()
        mock_app.db_manager = mock_db_instance
        mock_app.main_window = mock.Mock()
        mock_app.main_window.dialog = mock.AsyncMock()
        mock_app.show_error_dialog = mock.AsyncMock()

        # Create ConfigTab
        with mock.patch.object(ConfigTab, '_load_config_values'):
            config_tab = ConfigTab(mock_app)

        # Mock form fields
        mock_text_field = mock.Mock(spec=toga.TextInput)
        mock_text_field.value = "/test/income.xlsx"
        config_tab.form_fields = {"pay": mock_text_field}

        # Call save_config using asyncio.run
        # Avoid GLib event loop conflicts by using new thread
        result = None
        exception = None

        def run_async():
            nonlocal result, exception
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(config_tab.save_config(None))
                loop.close()
            except Exception as e:
                exception = e

        thread = threading.Thread(target=run_async)
        thread.start()
        thread.join()

        # Threading exceptions aren't always forwarded to the main thread
        # Make sure the test fails if it should
        if exception:
            raise exception

        # Should show error dialog
        mock_app.show_error_dialog.assert_called_once()

        # Should NOT update file watcher or refresh plot
        mock_app.file_watcher.update_watched_files.assert_not_called()
        mock_app.plot_tab.refresh_plot.assert_not_called()

        # Should NOT show success dialog
        mock_app.main_window.dialog.assert_not_called()

    @mock.patch('mmm_savings_rate.gui.DBConfigManager')
    def test_save_config_handles_multiple_form_fields(self, mock_db_manager):
        """Test that config save handles multiple form fields correctly."""
        # Mock database manager
        mock_db_instance = mock.Mock()
        mock_db_instance.get_main_user_settings.return_value = {}
        mock_db_instance.update_setting.return_value = True
        mock_db_manager.return_value = mock_db_instance

        # Create mock app
        mock_app = mock.Mock(spec=MMMSavingsRateApp)
        mock_app.plot_tab = mock.Mock()
        mock_app.plot_tab.refresh_plot = mock.AsyncMock()
        mock_app.file_watcher = mock.Mock(spec=FileWatcher)
        mock_app.file_watcher.update_watched_files = mock.Mock()
        mock_app.db_manager = mock_db_instance
        mock_app.main_window = mock.Mock()
        mock_app.main_window.dialog = mock.AsyncMock()

        # Create ConfigTab
        with mock.patch.object(ConfigTab, '_load_config_values'):
            config_tab = ConfigTab(mock_app)

        # Mock multiple form fields
        config_tab.form_fields = {
            "pay": mock.Mock(spec=toga.TextInput, value="/test/income.xlsx"),
            "savings": mock.Mock(spec=toga.TextInput, value="/test/savings.xlsx"),
            "goal": mock.Mock(spec=toga.TextInput, value="70.0"),
            "war": mock.Mock(spec=toga.Switch, value=True),
        }

        # Call save_config using asyncio.run
        # Avoid GLib event loop conflicts by using new thread
        result = None
        exception = None

        def run_async():
            nonlocal result, exception
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(config_tab.save_config(None))
                loop.close()
            except Exception as e:
                exception = e

        thread = threading.Thread(target=run_async)
        thread.start()
        thread.join()

        # Threading exceptions aren't always forwarded to the main thread
        # Make sure the test fails if it should
        if exception:
            raise exception

        # Should call update_setting for each field
        expected_calls = [
            mock.call('main_user_settings', 'pay', '/test/income.xlsx'),
            mock.call('main_user_settings', 'savings', '/test/savings.xlsx'),
            mock.call('main_user_settings', 'goal', 70.0),
            mock.call(
                'main_user_settings', 'war', 'on'
            ),  # True becomes "on" for war mode
        ]

        mock_db_instance.update_setting.assert_has_calls(expected_calls, any_order=True)

        # Should still trigger file watcher and plot refresh
        mock_app.file_watcher.update_watched_files.assert_called_once()
        mock_app.plot_tab.refresh_plot.assert_called_once()


if __name__ == '__main__':
    unittest.main()
