"""
MMM Savings Rate GUI using Beeware/Toga.

This module provides a graphical interface for the MMM Savings Rate application,
displaying Bokeh plots in a WebView and providing configuration management.
"""

import asyncio
import logging
import os
import platform
import subprocess
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
import toga
from toga.style import Pack
from toga.style.pack import COLUMN, ROW
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from .db_config import CONFIG_DIR_NAME, ERROR_LOG_FILENAME, DBConfigManager
from .savings_rate import Plot, SavingsRate, SRConfig


class FileWatcher:
    """File watcher that monitors spreadsheet files for changes and triggers plot refresh."""

    def __init__(self, app):
        self.app = app
        self.observer = Observer()
        self.watched_files = set()
        self.event_handler = self.SpreadsheetChangeHandler(self)
        self._debounce_timer = None
        self._debounce_delay = 1.0  # 1 second debounce
        self._setup_logging()

    def _setup_logging(self):
        """Set up logging to use the same error.log file as the rest of the application."""
        # Use the same log file path as DBConfigManager
        home_dir = Path.home()
        log_dir = home_dir / CONFIG_DIR_NAME
        log_file = log_dir / ERROR_LOG_FILENAME

        self.logger = logging.getLogger('file_watcher')
        self.logger.setLevel(logging.INFO)

        # Check if handler already exists to avoid duplicates
        if not self.logger.handlers:
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(logging.INFO)
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)

    class SpreadsheetChangeHandler(FileSystemEventHandler):
        """Handle file system events for spreadsheet files."""

        def __init__(self, watcher):
            self.watcher = watcher

        def on_modified(self, event):
            """Handle file modification events."""
            if event.is_directory:
                return

            # Check if the modified file is one we're watching
            file_path = os.path.abspath(event.src_path)
            if file_path in self.watcher.watched_files:
                # Check if it's a spreadsheet file
                if file_path.lower().endswith(('.xlsx', '.csv')):
                    self.watcher._trigger_refresh_debounced()

    def _trigger_refresh_debounced(self):
        """Trigger plot refresh with debouncing to avoid multiple rapid refreshes."""
        # Cancel existing timer
        if self._debounce_timer is not None:
            self._debounce_timer.cancel()

        # Start new timer
        self._debounce_timer = threading.Timer(
            self._debounce_delay, self._execute_refresh
        )
        self._debounce_timer.start()

    def _execute_refresh(self):
        """Execute the actual plot refresh in the main thread."""
        try:
            # Get the main event loop and schedule the coroutine
            loop = self.app._impl.loop if hasattr(self.app, '_impl') else None
            if loop and loop.is_running():
                # Schedule the coroutine on the main loop from our thread
                asyncio.run_coroutine_threadsafe(self.app.plot_tab.refresh_plot(), loop)
            else:
                # Fallback: try to find the running loop
                try:
                    loop = asyncio.get_running_loop()
                    asyncio.run_coroutine_threadsafe(
                        self.app.plot_tab.refresh_plot(), loop
                    )
                except RuntimeError:
                    self.logger.error(
                        "Could not find running event loop for plot refresh"
                    )

        except Exception as e:
            self.logger.error(f"Error refreshing plot after file change: {e}")

    def watch_file(self, file_path):
        """Add a file to the watch list."""
        if not file_path or not os.path.exists(file_path):
            return

        # Defensive programming: make sure the path is absolute
        abs_path = os.path.abspath(file_path)
        if abs_path not in self.watched_files:
            # Watch the directory containing the file
            directory = os.path.dirname(abs_path)
            try:
                self.observer.schedule(self.event_handler, directory, recursive=False)
                self.watched_files.add(abs_path)
                self.logger.info(f"Now watching: {abs_path}")
            except Exception as e:
                self.logger.error(f"Error watching file {abs_path}: {e}")

    def unwatch_file(self, file_path):
        """Remove a file from the watch list."""
        if not file_path:
            return

        abs_path = os.path.abspath(file_path)
        if abs_path in self.watched_files:
            self.watched_files.remove(abs_path)
            self.logger.info(f"Stopped watching: {abs_path}")

    def start(self):
        """Start the file observer."""
        if not self.observer.is_alive():
            try:
                self.observer.start()
                self.logger.info("File watcher started")
            except Exception as e:
                self.logger.error(f"Error starting file watcher: {e}")

    def stop(self):
        """Stop the file observer."""
        if self.observer.is_alive():
            self.observer.stop()
            self.observer.join()
            self.logger.info("File watcher stopped")

    def update_watched_files(self):
        """Update the list of watched files based on current configuration."""
        try:
            settings = self.app.db_manager.get_main_user_settings()

            # Clear current watches (simplified approach - restart observer)
            self.stop()
            self.observer = Observer()
            self.watched_files.clear()

            # Add current configured files
            pay_file = settings.get('pay', '')
            savings_file = settings.get('savings', '')

            if pay_file:
                self.watch_file(pay_file)
            if savings_file:
                self.watch_file(savings_file)

            self.start()

        except Exception as e:
            self.logger.error(f"Error updating watched files: {e}")


class MMMSavingsRateApp(toga.App):
    """Main Toga application for MMM Savings Rate."""

    def startup(self):
        """Initialize the application and create the main window."""
        self.main_window = toga.MainWindow(title=self.formal_name)

        # Create application menu
        self._create_app_menu()

        # Initialize database manager (for validation only)
        self.db_manager = DBConfigManager()
        if not self.db_manager.initialize_db():
            self.show_error_dialog("Database Error", ["Failed to initialize database"])
            return

        # Initialize file watcher
        self.file_watcher = FileWatcher(self)

        # Create main container
        self.main_box = toga.Box(style=Pack(direction=COLUMN, padding=10))

        # Initialize tabs
        self.plot_tab = PlotTab(self)
        self.config_tab = ConfigTab(self)
        self.income_tab = IncomeTab(self)
        self.savings_tab = SavingsTab(self)

        # Create tab container with initial content
        self.tab_container = toga.OptionContainer(
            content=[
                toga.OptionItem("Plot", self.plot_tab.content),
                toga.OptionItem("Config", self.config_tab.content),
                toga.OptionItem("Income", self.income_tab.content),
                toga.OptionItem("Savings", self.savings_tab.content),
            ],
            style=Pack(flex=1),
        )

        self.main_box.add(self.tab_container)
        self.main_window.content = self.main_box
        self.main_window.show()

        # Start file watcher and schedule initial simulation
        self.file_watcher.update_watched_files()

        # Schedule initial simulation to run after startup
        import asyncio

        asyncio.create_task(self.plot_tab.refresh_plot())

    async def run_simulation(self, widget):
        """Run the savings rate simulation using the existing CLI logic directly."""
        try:
            # Get GUI output path
            output_path = self.get_gui_output_path()

            config = SRConfig(user_id=1)
            savings_rate = SavingsRate(config)
            monthly_rates = savings_rate.get_monthly_savings_rates()
            user_plot = Plot(savings_rate)
            user_plot.plot_savings_rates(
                monthly_rates, embed=True, output_path=output_path
            )

        except Exception as e:
            # Parse error message and redirect to config tab
            error_msg = str(e)
            await self.show_error_dialog("Simulation Error", [error_msg])
            # Switch to Config tab if there's an error
            self.tab_container.current_tab = self.tab_container.content[1]  # Config tab
            return

    def get_gui_output_path(self) -> str:
        """Get the fixed output path for GUI plots."""
        home_dir = Path.home()
        config_dir = home_dir / CONFIG_DIR_NAME
        config_dir.mkdir(exist_ok=True)
        return str(config_dir / 'output.html')

    async def show_error_dialog(self, title: str, errors: List[str]):
        """Show an error dialog with the given title and error messages."""
        message = "\n".join(f"• {error}" for error in errors)
        await self.main_window.dialog(toga.ErrorDialog(title, message))

    def finalize(self):
        """Clean up resources when app shuts down."""
        try:
            if hasattr(self, 'file_watcher'):
                self.file_watcher.stop()
        except Exception as e:
            # Use file_watcher's logger if available, otherwise fallback to print
            if hasattr(self, 'file_watcher') and hasattr(self.file_watcher, 'logger'):
                self.file_watcher.logger.error(f"Error stopping file watcher: {e}")
            else:
                print(f"Error stopping file watcher: {e}")
        super().finalize()

    def _create_app_menu(self):
        """Create the application menu."""
        # Create View menu with refresh option
        view_menu = toga.Group('View')
        self.commands.add(
            toga.Command(
                self._menu_refresh_plot,
                text='Refresh Plot',
                tooltip='Refresh the plot display',
                group=view_menu,
                section=0,
            )
        )

    async def _menu_refresh_plot(self, widget):
        """Menu handler for refreshing the plot."""
        await self.plot_tab.refresh_plot()


def load_spreadsheet_data(file_path: str, limit: int = 10) -> Optional[Dict]:
    """
    Load data from a spreadsheet file and return the last N rows.

    Args:
        file_path: Path to the spreadsheet file
        limit: Number of rows to return (default 10)

    Returns:
        Dict with 'data', 'columns', 'file_info' or None if error
    """
    try:
        if not os.path.exists(file_path):
            return None

        # Get file info
        file_stat = os.stat(file_path)
        file_info = {
            'path': file_path,
            'size': file_stat.st_size,
            'modified': datetime.fromtimestamp(file_stat.st_mtime).strftime(
                '%Y-%m-%d %H:%M:%S'
            ),
        }

        # Load data based on file extension
        if file_path.lower().endswith('.xlsx'):
            df = pd.read_excel(file_path)
        elif file_path.lower().endswith('.csv'):
            df = pd.read_csv(file_path)
        else:
            return None

        # Get the last N rows (most recent at top when reversed)
        recent_data = df.tail(limit).iloc[::-1]  # Reverse for most recent first

        # Convert to list of dictionaries for table display
        data_rows = []
        for _, row in recent_data.iterrows():
            data_rows.append([str(val) if pd.notna(val) else "" for val in row.values])

        return {
            'data': data_rows,
            'columns': list(df.columns),
            'file_info': file_info,
            'total_rows': len(df),
        }

    except Exception as e:
        print(f"Error loading spreadsheet {file_path}: {e}")
        return None


class PlotTab:
    """Tab for displaying Bokeh plots in a WebView."""

    def __init__(self, app: MMMSavingsRateApp):
        self.app = app
        self.content = self._create_content()

    def _create_content(self):
        """Create the plot tab content."""
        box = toga.Box(style=Pack(direction=COLUMN, padding=10))

        # WebView for plot display
        self.webview = toga.WebView(style=Pack(flex=1))
        box.add(self.webview)

        # Initial placeholder
        self._show_placeholder()

        return box

    def _show_placeholder(self):
        """Show placeholder message when no plot is available."""
        placeholder_html = """
        <html>
        <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
            <h2>No Plot Available</h2>
            <p>Run simulation to view your savings rate plot.</p>
            <p>Check the Config tab for settings.</p>
        </body>
        </html>
        """
        self.webview.set_content("", placeholder_html)

    async def refresh_plot(self, widget=None):
        """Run simulation and refresh the plot display."""
        # First run the simulation to generate new plot
        await self.app.run_simulation(widget)

        # Then load the generated HTML content
        output_path = self.app.get_gui_output_path()
        if os.path.exists(output_path):
            try:
                # Read HTML content and set it directly in WebView
                with open(output_path, 'r', encoding='utf-8') as f:
                    html_content = f.read()

                # Use set_content with base URL to handle relative resources
                base_url = f"file://{os.path.dirname(output_path)}/"
                self.webview.set_content(base_url, html_content)
            except Exception as e:
                print(f"Error loading plot HTML: {e}")
                self._show_placeholder()
        else:
            self._show_placeholder()


class ConfigTab:
    """Tab for editing configuration settings."""

    def __init__(self, app: MMMSavingsRateApp):
        self.app = app
        self.form_fields = {}
        self.content = self._create_content()
        self._load_config_values()

    def _create_content(self):
        """Create the config tab content."""
        main_box = toga.Box(style=Pack(direction=COLUMN, padding=10))

        # Title
        title = toga.Label(
            'Configuration Settings',
            style=Pack(font_size=16, font_weight='bold', padding=(0, 0, 20, 0)),
        )
        main_box.add(title)

        # Scrollable container for form fields
        scroll_container = toga.ScrollContainer(style=Pack(flex=1))
        form_box = toga.Box(style=Pack(direction=COLUMN, padding=10))

        # File paths section
        self._add_section_title(form_box, "File Paths")
        self._add_text_field(
            form_box, "pay", "Income File Path:", "Path to income/pay spreadsheet file"
        )
        self._add_text_field(
            form_box,
            "savings",
            "Savings File Path:",
            "Path to savings spreadsheet file",
        )

        # Column mappings section
        self._add_section_title(form_box, "Column Mappings")
        self._add_text_field(
            form_box,
            "pay_date",
            "Income Date Column:",
            "Column name for dates in income file",
        )
        self._add_text_field(
            form_box,
            "gross_income",
            "Gross Income Column:",
            "Column name for gross income amounts",
        )
        self._add_text_field(
            form_box,
            "employer_match",
            "Employer Match Column:",
            "Column name for employer match amounts",
        )
        self._add_text_field(
            form_box,
            "savings_date",
            "Savings Date Column:",
            "Column name for dates in savings file",
        )

        # Array fields section
        self._add_section_title(form_box, "Account Lists (comma-separated)")
        self._add_text_field(
            form_box,
            "taxes_and_fees",
            "Tax/Fee Columns:",
            "Comma-separated list of tax and fee column names",
        )
        self._add_text_field(
            form_box,
            "savings_accounts",
            "Savings Account Columns:",
            "Comma-separated list of savings account column names",
        )

        # Options section
        self._add_section_title(form_box, "Display Options")
        self._add_switch_field(form_box, "show_average", "Show Average")
        self._add_switch_field(form_box, "war", "War Mode")

        # FRED API section
        self._add_section_title(form_box, "FRED API (Optional)")
        self._add_text_field(
            form_box,
            "fred_api_key",
            "FRED API Key:",
            "API key for Federal Reserve Economic Data",
        )

        # Notes and goals section
        self._add_section_title(form_box, "Notes and Goals")
        self._add_text_field(
            form_box,
            "notes",
            "Chart Notes Column:",
            "Column name for chart annotations",
        )
        self._add_text_field(
            form_box,
            "percent_fi_notes",
            "FI Percentage Notes Column:",
            "Column name for FI percentage annotations",
        )
        self._add_text_field(
            form_box,
            "goal",
            "Savings Goal:",
            "Target savings rate percentage (optional)",
        )
        self._add_text_field(
            form_box,
            "fi_number",
            "FI Target Amount:",
            "Financial independence target amount (optional)",
        )

        scroll_container.content = form_box
        main_box.add(scroll_container)

        # Buttons
        button_box = toga.Box(style=Pack(direction=ROW, padding=(20, 0, 0, 0)))

        self.validate_button = toga.Button(
            'Validate Config',
            on_press=self.validate_config,
            style=Pack(padding=(0, 10, 0, 0)),
        )
        button_box.add(self.validate_button)

        self.save_button = toga.Button(
            'Save Config', on_press=self.save_config, style=Pack(padding=(0, 10, 0, 0))
        )
        button_box.add(self.save_button)

        self.refresh_plot_button = toga.Button(
            'Refresh Plot',
            on_press=self.refresh_plot,
            style=Pack(padding=(0, 10, 0, 0)),
        )
        button_box.add(self.refresh_plot_button)

        main_box.add(button_box)

        return main_box

    def _add_section_title(self, container, title):
        """Add a section title to the form."""
        label = toga.Label(
            title, style=Pack(font_size=14, font_weight='bold', padding=(20, 0, 10, 0))
        )
        container.add(label)

    def _add_text_field(self, container, key, label_text, placeholder=""):
        """Add a text input field to the form."""
        field_box = toga.Box(style=Pack(direction=ROW, padding=(0, 0, 10, 0)))

        label = toga.Label(
            label_text, style=Pack(width=200, text_align='right', padding=(0, 10, 0, 0))
        )
        field_box.add(label)

        text_input = toga.TextInput(placeholder=placeholder, style=Pack(flex=1))
        self.form_fields[key] = text_input
        field_box.add(text_input)

        container.add(field_box)

    def _add_multiline_field(self, container, key, label_text):
        """Add a multiline text input field to the form."""
        field_box = toga.Box(style=Pack(direction=COLUMN, padding=(0, 0, 10, 0)))

        label = toga.Label(label_text, style=Pack(padding=(0, 0, 5, 0)))
        field_box.add(label)

        text_input = toga.MultilineTextInput(style=Pack(height=80, width=400))
        self.form_fields[key] = text_input
        field_box.add(text_input)

        container.add(field_box)

    def _add_switch_field(self, container, key, label_text):
        """Add a switch/toggle field to the form."""
        field_box = toga.Box(style=Pack(direction=ROW, padding=(0, 0, 10, 0)))

        switch = toga.Switch(text=label_text, style=Pack(padding=(0, 10, 0, 0)))
        self.form_fields[key] = switch
        field_box.add(switch)

        container.add(field_box)

    def _add_selection_field(self, container, key, label_text, options):
        """Add a selection field to the form."""
        field_box = toga.Box(style=Pack(direction=ROW, padding=(0, 0, 10, 0)))

        label = toga.Label(
            label_text, style=Pack(width=200, text_align='right', padding=(0, 10, 0, 0))
        )
        field_box.add(label)

        selection = toga.Selection(items=options)
        self.form_fields[key] = selection
        field_box.add(selection)

        container.add(field_box)

    def _load_config_values(self):
        """Load current configuration values into form fields."""
        try:
            settings = self.app.db_manager.get_main_user_settings()

            for key, field in self.form_fields.items():
                value = settings.get(key, "")
                self._set_field_value(field, key, value)

        except Exception as e:
            print(f"Error loading config values: {e}")

    def _set_field_value(self, field, key, value):
        """Set a form field value based on field type and key."""
        if isinstance(field, toga.TextInput):
            self._handle_text_input(field, key, value)
        elif isinstance(field, toga.MultilineTextInput):
            self._handle_multiline_text_input(field, key, value)
        elif isinstance(field, toga.Switch):
            self._handle_switch(field, key, value)
        elif isinstance(field, toga.Selection):
            self._handle_selection(field, key, value)

    def _handle_text_input(self, field, key, value):
        """Handle TextInput field value setting."""
        if key in ["taxes_and_fees", "savings_accounts"]:
            # Handle array fields - convert to comma-separated string
            if isinstance(value, list):
                field.value = ", ".join(str(item) for item in value)
            else:
                field.value = str(value) if value is not None else ""
        else:
            # Handle all other text fields uniformly
            field.value = str(value) if value is not None else ""

    def _handle_multiline_text_input(self, field, key, value):
        """Handle MultilineTextInput field value setting."""
        field.value = str(value) if value is not None else ""

    def _handle_switch(self, field, key, value):
        """Handle Switch field value setting."""
        if key == "war":
            # War mode uses string "on"/"off" values
            field.value = str(value).lower() == "on"
        else:
            # Other switches use boolean values
            field.value = bool(value)

    def _handle_selection(self, field, key, value):
        """Handle Selection field value setting."""
        if str(value) in [str(item) for item in field.items]:
            field.value = str(value)

    def _get_form_values(self):
        """Get current values from form fields."""
        values = {}

        for key, field in self.form_fields.items():
            values[key] = self._extract_field_value(field, key)

        return values

    def _extract_field_value(self, field, key):
        """Extract and convert a form field value to database format."""
        if isinstance(field, toga.TextInput):
            return self._extract_text_input_value(field, key)
        elif isinstance(field, toga.MultilineTextInput):
            return self._extract_multiline_text_input_value(field, key)
        elif isinstance(field, toga.Switch):
            return self._extract_switch_value(field, key)
        elif isinstance(field, toga.Selection):
            return self._extract_selection_value(field, key)
        else:
            return field.value

    def _extract_text_input_value(self, field, key):
        """Extract and convert TextInput field value."""
        value = field.value.strip()

        if key in ["taxes_and_fees", "savings_accounts"]:
            # Handle array fields - convert comma-separated string to list
            if value:
                return [item.strip() for item in value.split(",") if item.strip()]
            else:
                return []
        elif key in ["goal", "fi_number"]:
            # Handle numeric fields - convert to float or None
            return float(value) if value else None
        else:
            # Handle regular text fields
            return value

    def _extract_multiline_text_input_value(self, field, key):
        """Extract MultilineTextInput field value."""
        return field.value.strip()

    def _extract_switch_value(self, field, key):
        """Extract Switch field value with special handling for war mode."""
        if key == "war":
            # War mode uses string "on"/"off" values
            return "on" if field.value else "off"
        else:
            # Other switches use boolean values
            return field.value

    def _extract_selection_value(self, field, key):
        """Extract Selection field value."""
        return field.value

    async def validate_config(self, widget):
        """Validate the current configuration using direct validation logic."""
        try:
            # Use the validation logic directly
            is_valid, errors = self.app.db_manager.validate_config()

            if is_valid:
                await self.app.main_window.dialog(
                    toga.InfoDialog("Validation", "✓ Configuration is valid")
                )
            else:
                error_messages = [f"- {error}" for error in errors]
                await self.app.show_error_dialog("Configuration Errors", error_messages)

        except Exception as e:
            await self.app.show_error_dialog("Validation Error", [str(e)])

    async def refresh_plot(self, widget):
        """Refresh the plot display."""
        await self.app.plot_tab.refresh_plot()

    async def save_config(self, widget):
        """Save configuration changes."""
        try:
            # Get values from form
            form_values = self._get_form_values()

            # Save each setting using the database manager
            for key, value in form_values.items():
                success = self.app.db_manager.update_setting(
                    'main_user_settings', key, value
                )
                if not success:
                    await self.app.show_error_dialog(
                        "Save Error", [f"Failed to save setting: {key}"]
                    )
                    return

            # Show success message
            await self.app.main_window.dialog(
                toga.InfoDialog("Save", "✓ Configuration saved successfully")
            )

            # Update file watcher with new configuration
            self.app.file_watcher.update_watched_files()

            # Auto-refresh the plot with new configuration
            await self.app.plot_tab.refresh_plot()

        except Exception as e:
            await self.app.show_error_dialog(
                "Save Error", [f"Failed to save configuration: {str(e)}"]
            )


class DataTab:
    """Base class for data viewing tabs (Income/Savings)."""

    def __init__(self, app: MMMSavingsRateApp, tab_name: str, config_key: str):
        self.app = app
        self.tab_name = tab_name
        self.config_key = config_key  # 'pay' or 'savings'
        self.data_table = None
        self.content = self._create_content()
        # Load initial data
        self._load_data()

    def _create_content(self):
        """Create the data tab content."""
        box = toga.Box(style=Pack(direction=COLUMN, padding=10))

        # Title and file info
        self.title_label = toga.Label(
            f'{self.tab_name} Data',
            style=Pack(font_size=16, font_weight='bold', padding=(0, 0, 10, 0)),
        )
        box.add(self.title_label)

        self.file_info_label = toga.Label(
            'Loading file information...', style=Pack(padding=(0, 0, 10, 0))
        )
        box.add(self.file_info_label)

        # Buttons
        button_box = toga.Box(style=Pack(direction=ROW, padding=(0, 0, 10, 0)))

        self.reload_button = toga.Button(
            'Reload Data', on_press=self.reload_data, style=Pack(padding=(0, 10, 0, 0))
        )
        button_box.add(self.reload_button)

        self.open_button = toga.Button(
            'Open Spreadsheet',
            on_press=self.open_spreadsheet,
            style=Pack(padding=(0, 0, 0, 10)),
        )
        button_box.add(self.open_button)

        box.add(button_box)

        # Scrollable container for the data table
        self.scroll_container = toga.ScrollContainer(style=Pack(flex=1))

        # Placeholder that will be replaced with actual table
        self.table_placeholder = toga.Label('Loading data...', style=Pack(padding=10))
        self.scroll_container.content = self.table_placeholder

        box.add(self.scroll_container)

        return box

    def _get_file_path(self):
        """Get the file path for this tab's data."""
        try:
            settings = self.app.db_manager.get_main_user_settings()
            return settings.get(self.config_key, "")
        except Exception:
            return ""

    def _load_data(self):
        """Load and display data from the spreadsheet."""
        try:
            file_path = self._get_file_path()
            if not file_path:
                self._show_no_file_configured()
                return

            # Load spreadsheet data
            data_result = load_spreadsheet_data(file_path, limit=10)
            if not data_result:
                self._show_file_error(file_path)
                return

            # Update file info label
            file_info = data_result['file_info']
            self.file_info_label.text = (
                f"File: {file_info['path']}\n"
                f"Last Modified: {file_info['modified']} | "
                f"Total Rows: {data_result['total_rows']} | "
                f"Showing: {len(data_result['data'])} most recent"
            )

            # Create data table
            self._create_data_table(data_result['columns'], data_result['data'])

        except Exception as e:
            self._show_error(f"Error loading data: {str(e)}")

    def _create_data_table(self, columns: List[str], data_rows: List[List[str]]):
        """Create and display the data table."""
        try:
            # Create table with headings and data
            headings = columns

            # Create Table widget
            self.data_table = toga.Table(
                headings=headings, data=data_rows, style=Pack(flex=1)
            )

            # Replace placeholder with table
            self.scroll_container.content = self.data_table

        except Exception as e:
            self._show_error(f"Error creating table: {str(e)}")

    def _show_no_file_configured(self):
        """Show message when no file is configured."""
        self.file_info_label.text = f"No {self.tab_name.lower()} file configured"
        message = toga.Label(
            f"Configure the {self.tab_name.lower()} file path in the Config tab.",
            style=Pack(padding=10),
        )
        self.scroll_container.content = message

    def _show_file_error(self, file_path: str):
        """Show message when file cannot be loaded."""
        self.file_info_label.text = f"Error loading file: {os.path.basename(file_path)}"
        message = toga.Label(
            f"Could not load {self.tab_name.lower()} file:\n{file_path}\n\n"
            "Check that the file exists and is a valid .xlsx or .csv file.",
            style=Pack(padding=10),
        )
        self.scroll_container.content = message

    def _show_error(self, error_message: str):
        """Show generic error message."""
        message = toga.Label(error_message, style=Pack(padding=10))
        self.scroll_container.content = message

    async def reload_data(self, widget):
        """Reload data from spreadsheet."""
        self._load_data()

    async def open_spreadsheet(self, widget):
        """Open spreadsheet in external application."""
        try:
            file_path = self._get_file_path()
            if not file_path or not os.path.exists(file_path):
                await self.app.show_error_dialog(
                    "File Not Found",
                    [f"Could not find {self.tab_name.lower()} file: {file_path}"],
                )
                return

            # Ensure file watcher is watching this file
            self.app.file_watcher.watch_file(file_path)

            # Open file with default application (cross-platform)
            system = platform.system()
            if system == 'Windows':
                os.startfile(file_path)
            elif system == 'Darwin':  # macOS
                subprocess.run(['open', file_path], check=False)
            else:  # Linux and other Unix-like systems
                subprocess.run(['xdg-open', file_path], check=False)

        except Exception as e:
            await self.app.show_error_dialog(
                "Open Error", [f"Could not open {self.tab_name.lower()} file: {str(e)}"]
            )


class IncomeTab(DataTab):
    """Tab for viewing income data."""

    def __init__(self, app: MMMSavingsRateApp):
        super().__init__(app, "Income", "pay")


class SavingsTab(DataTab):
    """Tab for viewing savings data."""

    def __init__(self, app: MMMSavingsRateApp):
        super().__init__(app, "Savings", "savings")


def main():
    """Entry point for briefcase - returns app object."""
    return MMMSavingsRateApp('MMM Savings Rate', 'com.savingsratewars')


def run_gui():
    """Entry point for console script - runs the application."""
    app = main()
    app.main_loop()


if __name__ == '__main__':
    run_gui()
