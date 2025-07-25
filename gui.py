"""
MMM Savings Rate GUI using Beeware/Toga.

This module provides a graphical interface for the MMM Savings Rate application,
displaying Bokeh plots in a WebView and providing configuration management.
"""

import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
import toga
from toga.style import Pack
from toga.style.pack import COLUMN, ROW

from db_config import DBConfigManager


class MMMSavingsRateApp(toga.App):
    """Main Toga application for MMM Savings Rate."""

    def startup(self):
        """Initialize the application and create the main window."""
        self.main_window = toga.MainWindow(title=self.formal_name)

        # Initialize database manager (for validation only)
        self.db_manager = DBConfigManager()
        if not self.db_manager.initialize_db():
            self.show_error_dialog("Database Error", ["Failed to initialize database"])
            return

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

        # Schedule initial simulation to run after startup
        import asyncio

        asyncio.create_task(self.plot_tab.refresh_plot())

    async def run_simulation(self, widget):
        """Run the savings rate simulation using the existing CLI command."""
        try:
            # Get GUI output path
            output_path = self.get_gui_output_path()

            # Set environment variable to prevent Bokeh from opening browser
            env = os.environ.copy()
            env['BOKEH_BROWSER'] = 'none'

            # Run the existing CLI command
            result = subprocess.run(
                ['savingsrates', '--output', output_path],
                capture_output=True,
                text=True,
                cwd=os.getcwd(),
                env=env,
            )

            if result.returncode != 0:
                # Parse error message and redirect to config tab
                error_msg = (
                    result.stderr.strip() if result.stderr else "Unknown error occurred"
                )
                await self.show_error_dialog("Simulation Error", [error_msg])
                # Switch to Config tab if there's an error
                self.tab_container.current_tab = self.tab_container.content[
                    1
                ]  # Config tab
                return

            # Simulation successful - HTML file should now exist

        except FileNotFoundError:
            await self.show_error_dialog(
                "Command Not Found",
                [
                    "Could not find 'savingsrates' command. Make sure the package is installed properly."
                ],
            )
        except Exception as e:
            await self.show_error_dialog(
                "Simulation Error", [f"Unexpected error: {str(e)}"]
            )

    def get_gui_output_path(self) -> str:
        """Get the fixed output path for GUI plots."""
        home_dir = Path.home()
        config_dir = home_dir / '.mmm_savings_rate'
        config_dir.mkdir(exist_ok=True)
        return str(config_dir / 'output.html')

    async def show_error_dialog(self, title: str, errors: List[str]):
        """Show an error dialog with the given title and error messages."""
        message = "\n".join(f"• {error}" for error in errors)
        await self.main_window.dialog(toga.ErrorDialog(title, message))


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

        # Refresh button at bottom (now runs full simulation)
        self.refresh_button = toga.Button(
            'Refresh Plot',
            on_press=self.refresh_plot,
            style=Pack(padding=(10, 0, 0, 0)),
        )
        box.add(self.refresh_button)

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
            'Save Config', on_press=self.save_config, style=Pack(padding=(0, 0, 0, 10))
        )
        button_box.add(self.save_button)

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

                if isinstance(field, toga.TextInput):
                    # Handle array fields (taxes_and_fees, savings_accounts are arrays)
                    if key in ["taxes_and_fees", "savings_accounts"]:
                        if isinstance(value, list):
                            field.value = ", ".join(str(item) for item in value)
                        else:
                            field.value = str(value) if value is not None else ""
                    # Handle single column fields (notes, percent_fi_notes are single strings)
                    elif key in ["notes", "percent_fi_notes"]:
                        field.value = str(value) if value is not None else ""
                    else:
                        field.value = str(value) if value is not None else ""
                elif isinstance(field, toga.MultilineTextInput):
                    field.value = str(value) if value is not None else ""
                elif isinstance(field, toga.Switch):
                    # Handle war mode (string) vs show_average (boolean)
                    if key == "war":
                        field.value = str(value).lower() == "on"
                    else:
                        field.value = bool(value)
                elif isinstance(field, toga.Selection):
                    # Set selection value
                    if str(value) in [str(item) for item in field.items]:
                        field.value = str(value)

        except Exception as e:
            print(f"Error loading config values: {e}")

    def _get_form_values(self):
        """Get current values from form fields."""
        values = {}

        for key, field in self.form_fields.items():
            if isinstance(field, toga.TextInput):
                value = field.value.strip()

                # Handle array fields (only taxes_and_fees and savings_accounts are arrays)
                if key in ["taxes_and_fees", "savings_accounts"]:
                    if value:
                        values[key] = [
                            item.strip() for item in value.split(",") if item.strip()
                        ]
                    else:
                        values[key] = []
                # Handle numeric fields
                elif key in ["goal", "fi_number"]:
                    values[key] = float(value) if value else None
                else:
                    values[key] = value

            elif isinstance(field, toga.MultilineTextInput):
                values[key] = field.value.strip()

            elif isinstance(field, toga.Switch):
                # Handle war mode (string) vs show_average (boolean)
                if key == "war":
                    values[key] = "on" if field.value else "off"
                else:
                    values[key] = field.value

            elif isinstance(field, toga.Selection):
                values[key] = field.value

        return values

    async def validate_config(self, widget):
        """Validate the current configuration using existing CLI validation."""
        try:
            result = subprocess.run(
                ['sr-validate-config'], capture_output=True, text=True
            )

            if result.returncode == 0:
                await self.app.main_window.dialog(
                    toga.InfoDialog("Validation", "✓ Configuration is valid")
                )
            else:
                error_msg = (
                    result.stderr.strip() if result.stderr else result.stdout.strip()
                )
                await self.app.show_error_dialog("Configuration Errors", [error_msg])

        except FileNotFoundError:
            await self.app.show_error_dialog(
                "Command Not Found", ["Could not find 'sr-validate-config' command"]
            )
        except Exception as e:
            await self.app.show_error_dialog("Validation Error", [str(e)])

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

            # Use xdg-open on Linux to open with default application
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
    """Entry point for the GUI application."""
    app = MMMSavingsRateApp('MMM Savings Rate', 'org.example.mmm_savings_rate')
    return app.main_loop()


if __name__ == '__main__':
    main()
