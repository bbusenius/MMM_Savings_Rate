MMM Savings Rate
================

MMM Savings Rate is a tool that allows users to calculate and track
their monthly savings rates over time. It uses the `FI
module <https://github.com/bbusenius/FI>`__ and plots savings rates with
`Bokeh <https://bokeh.org/>`__.

**Key Features:** - **Graphical User Interface (GUI)** - User-friendly
interface built with BeeWare/Toga - **Command Line Interface (CLI)** -
Full-featured command line tools - Parse Excel (.xlsx) and CSV
spreadsheets with flexible column mapping - Interactive web-based
visualizations with Bokeh - JSON-based configuration using TinyDB for
easy management - CLI commands for configuration management - Optional
FRED integration for US average savings rate comparison - “Enemy” mode
for competitive savings rate tracking - Python 3.10+ support with
automated code quality checks

Users simply enter their savings and income data into a spreadsheet.
Unique spreadsheet column headers are mapped to the application through
a JSON configuration file, allowing the utility to be used with any
custom spreadsheet. When the simulation runs, the user’s monthly savings
rates are plotted on an interactive line graph.

.. figure:: https://github.com/bbusenius/MMM_Savings_Rate/raw/master/docs/screenshot.png
   :alt: Example savings rates plotted

   Example savings rates plotted

Users may also supply secondary, “enemy” spreadsheets. This feature is
provided to make the experience fun, game-like, and competitive for
people who prefer such an experience. If an enemy spreadsheet is
provided, the enemy savings rates are plotted alongside those of the
main user. This feature is optional.

*MMM Savings Rate was inspired by Mr. Money Mustache. Visit the
Mr. Money Mustache website and* `read this article to learn
more <http://www.mrmoneymustache.com/2012/01/13/the-shockingly-simple-math-behind-early-retirement>`__\ *.*

Installation
------------

This package should generally be installed using pip.

For users (CLI only)
~~~~~~~~~~~~~~~~~~~~

.. code:: bash

   pip install git+https://github.com/bbusenius/MMM_Savings_Rate.git#egg=mmm_savings_rate

For users (CLI + GUI)
~~~~~~~~~~~~~~~~~~~~~

.. code:: bash

   pip install "git+https://github.com/bbusenius/MMM_Savings_Rate.git#egg=mmm_savings_rate[gui]"

For developers
~~~~~~~~~~~~~~

.. code:: bash

   # Clone and install in development mode with GUI support
   git clone https://github.com/bbusenius/MMM_Savings_Rate.git
   cd MMM_Savings_Rate
   pip install -e .[gui]

   # Install development dependencies for linting
   pip install -r requirements-dev.txt

| **Installation Options:** - **Core**: ``pip install -e .`` - CLI
  functionality only - **GUI**: ``pip install -e .[gui]`` - CLI + GUI
  functionality
| - **Development**: ``pip install -e .[gui] -r requirements-dev.txt`` -
  Everything + development tools ## Setting up the application

In order to get things going, you’ll only need to take the following
steps:

1. Setup a directory of spreadsheet files with the financial data needed
   to run the simulation.
2. Configuration: The application automatically creates a JSON
   configuration file at ``~/.mmm_savings_rate/db.json`` with default
   settings.
3. Customize your configuration using the CLI commands or by editing the
   JSON file directly.
4. Run the simulation command.

Spreadsheet files
~~~~~~~~~~~~~~~~~

MMM Savings Rate was designed to be flexible in order to work with a
variety of spreadsheets. At the moment, spreadsheets must be saved as
.xlsx or .csv files, however, column headers can be unique, so it
doesn’t matter what labels you use to categorize things. To get started
you’ll need financial data for both **income** and **savings**.

This data can exist in a single spreadsheet with other financial data or
it can exist in separate spreadsheets. How you set it up is your choice,
however, certain data is required. The application will allow you to map
your column labels to fields, so you don’t have to name them the same as
outlined here. You also might want to split some of these fields over
multiple columns in your spreadsheet. Jump to the configuration section
to learn how to do this. However you decide to enter the data in your
spreadsheet, all of the following fields must be represented in some
fashion.

-  **Date for pay** - the date of your paycheck or date associated with
   the income being entered. The application can parse most date
   formats.
-  **Gross Pay** - the amount of money you made in its entirety before
   taxes were withdrawn.
-  **Employer Match** - money contributed to a retirement plan by your
   employer.
-  **Taxes and Fees** - any taxes and fees taken out of your paycheck
   before it was delivered, e.g. FICA, Medicare, etc.
-  **Savings Accounts** - a dollar amount (mapped to 1 or multiple
   accounts)
-  **Date for savings** - the date you saved money into each account.

*Note about “Savings Accounts”: you might have multiple savings
accounts, e.g. Bank Account, Vanguard Brokerage, Roth. Each one of these
would contain a dollar amount representing the quantity of money saved
for the month. Mapping will be handled in the configuration stage.*

`For example spreadsheets please look in the csv
directory <https://github.com/bbusenius/MMM_Savings_Rate/tree/master/csv>`__.
This should give you a good idea of how to lay things out.

Configuration
~~~~~~~~~~~~~

MMM Savings Rate uses a single JSON configuration file to manage all
settings. The application automatically creates and manages this file at
``~/.mmm_savings_rate/db.json``.

Automatic Configuration Setup
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

When you first run the application, it will automatically: 1. Create the
configuration directory at ``~/.mmm_savings_rate/`` 2. Initialize a
``db.json`` file with default settings 3. Set up error logging to
``~/.mmm_savings_rate/error.log``

Configuration Management
^^^^^^^^^^^^^^^^^^^^^^^^

You can manage your configuration in three ways:

**Option 1: GUI Configuration**

Use the Config tab in the graphical interface for visual configuration
editing with validation:

.. code:: bash

   # Launch the GUI
   mmm-savings-rate-gui

Then navigate to the Config tab to edit all settings with form
validation and error checking.

**Option 2: CLI Commands**

.. code:: bash

   # View current configuration
   sr-show-config

   # Update a setting
   sr-update-setting main_user_settings pay "/path/to/income.xlsx"
   sr-update-setting main_user_settings savings "/path/to/savings.xlsx"

   # Validate configuration
   sr-validate-config

**Option 3: Editing the JSON directly** You can directly edit the
``~/.mmm_savings_rate/db.json`` file. Here’s an example configuration:

.. code:: json

   {
     "main_user_settings": {
       "pay": "/path/to/income.xlsx",
       "pay_date": "Date",
       "gross_income": "Gross Pay",
       "employer_match": "Employer Match",
       "taxes_and_fees": ["OASDI", "Medicare", "Federal Withholding", "State Tax", "FICA"],
       "savings": "/path/to/savings.xlsx",
       "savings_date": "Date",
       "savings_accounts": ["Vanguard Brokerage", "Vanguard 403b", "Vanguard Roth"],
       "notes": "Notes",
       "show_average": true,
       "war": "off",
       "fred_url": "https://api.stlouisfed.org/fred/series/observations?series_id=PSAVERT&file_type=json",
       "fred_api_key": "",
       "goal": 70.0,
       "fi_number": 1000000,
       "total_balances": "Total Balance",
       "percent_fi_notes": "Total Balance Notes"
     },
     "users": [
       {
         "_id": 1,
         "name": "User",
         "config_ref": "main_user_settings"
       }
     ],
     "enemy_settings": []
   }

Main settings
'''''''''''''

The majority of the main settings are listed under
``main_user_settings``. Settings include:

-  **pay** - a full path to your income spreadsheet.
-  **pay_date** - the name of a column header for the dates of income or
   payment transactions.
-  **savings** - a full path to your savings spreadsheet (can be the
   same file used for pay).
-  **savings_date** - the name of a column header for the dates of
   income or payment transactions.
-  **gross_income** - the name of a column header in your spreadsheet
   representing gross pay.
-  **employer_match** - the name of a column header in your spreadsheet
   that represents your employer match.
-  **taxes_and_fees** - the names of column headers in your spreadsheet
   containing taxes and fees.
-  **savings_accounts** - the names of column headers in your
   spreadsheet that contain savings data from an investment account or
   accounts.
-  **goal** - optional setting that allows you to set a savings rate
   goal that you’re trying to reach.
-  **war** - allows you to show or hide, “enemy” plots on your graph.
   Set this to, “off” if you only want to see your own data.

Additional settings
'''''''''''''''''''

US Average Savings Rates from FRED
                                  

Optional settings allow you to plot the average US savings rates
alongside your own. This data comes from the Federal Reserve Economic
Data (FRED) at the Federal Reserve Bank of St. Louis.

-  **fred_url** - the url of the FRED API endpoint.
-  **fred_api_key** - an API token to use FRED.

In order to use these settings, you will need to sign up for an account
with FRED and request an API token. This takes about 5 minutes and `can
be done on their
website <https://fred.stlouisfed.org/docs/api/api_key.html>`__.

Once you enable FRED, you will be able to see how your savings rates
dominate the US average\*.

.. figure:: https://github.com/bbusenius/MMM_Savings_Rate/raw/master/docs/FRED.png
   :alt: US average savings rates plotted

   US average savings rates plotted

\*US average savings rates calculated by FRED are generated after
removing outlays from personal income. Since outlays include purchases
of durable and non-durable goods, these savings rates are inflated. Even
so, as a Mustachian you will easily beat these averages.

Notes and goal
              

If you want to annotate points on your plot with text from your
spreadsheet, you can map a ``notes`` field. This should match a column
header on your spreadsheet. If you’re using separate spreadsheets for
savings and income, the application will look for the same column name
in both spreadsheets and de-dupe duplicate notes for the same month
while displaying all notes from both spreadsheets for the same month if
they’re unique.

-  **notes** - the name of a column header that maps to notes or special
   events that you want to show on your plot.

A goal can be added to your plot as well.

-  **goal** - numeric value of a savings rate goal you’d like to reach,
   e.g. 70.

.. figure:: https://github.com/bbusenius/MMM_Savings_Rate/raw/master/docs/notes.png
   :alt: Savings rates plotted with annotations

   Savings rates plotted with annotations

% FI
    

If you want to plot your progress towards FI as a percentage of your FI
number, you can enable this with the following settings in your
``db.json``:

-  **fi_number** - your FI number.
-  **total_balances** - a spreadsheet heading that maps to a column
   where you track the total monthly balance of all your accounts.
-  **percent_fi_notes** - a spreadsheet heading that maps to a column
   with text that you want to show on the % FI plot. Entries will appear
   as event dots on the plot and will display tooltips with the notes on
   hover.

This doesn’t take into account liabilities so, if you have them, you can
just as easily map these configurations to a column that tracks net
worth instead.

.. figure:: https://github.com/bbusenius/MMM_Savings_Rate/raw/master/docs/percent-fi-notes.png
   :alt: Percent FI plotted with annotations

   Percent FI plotted with annotations

Running the simulation
~~~~~~~~~~~~~~~~~~~~~~

Once you have your spreadsheet files ready and have configured your
settings, you can run the application:

1. **First run**: The application will automatically create the
   configuration file with defaults:

   .. code:: bash

      savingsrates

2. **Configure your settings** using CLI commands:

   .. code:: bash

      # Update file paths to point to your spreadsheets
      sr-update-setting main_user_settings pay "/path/to/your/income.xlsx"
      sr-update-setting main_user_settings savings "/path/to/your/savings.xlsx"

      # Update column mappings as needed
      sr-update-setting main_user_settings savings_accounts '["Account1", "Account2"]'

3. **Run the application**:

   .. code:: bash

      savingsrates

When you run the command, a plot of your monthly savings rates will open
in a browser window.

CLI Options
^^^^^^^^^^^

The ``savingsrates`` command supports the following optional arguments:

-  ``-u, --user USER_ID`` - Specify which user to analyze (default: 1)
-  ``-o, --output OUTPUT_PATH`` - Specify where to save the HTML plot
   file (default: savings-rates.html)

**Usage Examples:**

.. code:: bash

   # Generate plot with default settings (saves to savings-rates.html)
   savingsrates

   # Analyze a different user and save to a custom location
   savingsrates --user 2 --output my-savings-report.html

   # Save plot to a specific directory (directories will be created if needed)
   savingsrates -o ~/.mmm_savings_rate/plots/monthly-report.html

   # Save to an absolute path
   savingsrates -o /tmp/reports/savings-$(date +%Y%m%d).html

   # Get help and see all available options
   savingsrates --help

CLI Management Commands
^^^^^^^^^^^^^^^^^^^^^^^

The application now includes dedicated CLI commands for configuration
management:

-  ``sr-show-config`` - Display current configuration
-  ``sr-validate-config`` - Validate configuration and report any errors
-  ``sr-update-setting <table> <field> <value>`` - Update specific
   settings

Using the GUI
-------------

MMM Savings Rate includes a full-featured graphical user interface built
with BeeWare/Toga.

Installing the GUI
~~~~~~~~~~~~~~~~~~

**Option 1: Python Package (pip)**

.. code:: bash

   # Install with GUI support
   pip install "git+https://github.com/bbusenius/MMM_Savings_Rate.git#egg=mmm_savings_rate[gui]"

**Option 2: OS Package Installer**

.. code:: bash

   # Command line installation (Ubuntu/Debian)
   sudo dpkg -i mmm-savings-rate-2.0.0-1.deb

   # Or double-click the .deb file to install via Ubuntu App Center

..

   **Note**: Currently only ``.deb`` packages for Ubuntu/Debian are
   available. Other OS package formats may be added in future releases.

Launching the GUI
~~~~~~~~~~~~~~~~~

**If installed via .deb package:** - Launch like any other application
from your desktop environment (Activities menu, application launcher,
etc.) - Or run from command line: ``mmm-savings-rate-gui``

**If installed via pip:**

.. code:: bash

   # Start the GUI application
   mmm-savings-rate-gui

GUI Features
~~~~~~~~~~~~

The GUI provides an intuitive interface with four main tabs:

**📊 Plot Tab** (Default)
^^^^^^^^^^^^^^^^^^^^^^^^^

-  **Interactive Bokeh plots** displayed directly in the application
-  **Automatic simulation** runs on startup with your current
   configuration
-  **Refresh Plot button** to regenerate plots after making changes
-  **Responsive plots** that adapt to window size
-  **No browser required** - plots display within the GUI

.. figure:: docs/gui-plot-tab.png
   :alt: GUI Plot Tab

   GUI Plot Tab

**⚙️ Config Tab**
^^^^^^^^^^^^^^^^^

-  **Visual configuration editor** for all settings
-  **Organized sections**: File Paths, Column Mappings, Account Lists,
   Display Options, FRED API, Notes & Goals
-  **Form validation** with error checking and helpful messages
-  **Save & Validate** button to apply changes
-  **Automatic field type handling** (text, numbers, lists, checkboxes)
-  **Shares configuration** with CLI tools via
   ``~/.mmm_savings_rate/db.json``

.. figure:: docs/gui-config-tab.png
   :alt: GUI Config Tab

   GUI Config Tab

**💳 Income Tab**
^^^^^^^^^^^^^^^^^

-  **Read-only table view** of your income spreadsheet data
-  **Last 10 entries** displayed in reverse chronological order (most
   recent first)
-  **All spreadsheet columns** visible with scrollable table
-  **File information** showing path, last modified date, and total rows
-  **Reload Data** button to refresh after external spreadsheet changes
-  **Open Spreadsheet** button to edit files in external applications
   (Excel, LibreOffice, etc.)

.. figure:: docs/gui-income-tab.png
   :alt: GUI Income Tab

   GUI Income Tab

**💰 Savings Tab**
^^^^^^^^^^^^^^^^^^

-  **Read-only table view** of your savings spreadsheet data
-  **Last 10 entries** displayed in reverse chronological order (most
   recent first)
-  **All spreadsheet columns** visible with scrollable table
-  **File information** showing path, last modified date, and total rows
-  **Reload Data** button to refresh after external spreadsheet changes
-  **Open Spreadsheet** button to edit files in external applications

.. figure:: docs/gui-savings-tab.png
   :alt: GUI Savings Tab

   GUI Savings Tab

GUI Workflow
~~~~~~~~~~~~

**First-Run Experience**
^^^^^^^^^^^^^^^^^^^^^^^^

When you first launch the GUI without any configuration, you’ll see a
placeholder message prompting you to configure your settings:

.. figure:: docs/gui-first-run-1.png
   :alt: GUI First Run - No Plot Available

   GUI First Run - No Plot Available

After clicking “Cancel”, the GUI automatically creates default
configuration and takes you to the Config tab to get started:

.. figure:: docs/gui-first-run-2.png
   :alt: GUI First Run - Default Config

   GUI First Run - Default Config

**Typical Workflow**
^^^^^^^^^^^^^^^^^^^^

1. **First Run**: The GUI automatically creates default configuration at
   ``~/.mmm_savings_rate/db.json``
2. **Configure**: Use the Config tab to set your spreadsheet file paths
   and column mappings
3. **View Data**: Check Income and Savings tabs to verify your data is
   loading correctly
4. **Generate Plot**: Return to Plot tab and click “Refresh Plot” to
   generate your savings rate visualization
5. **Iterate**: Make configuration changes and refresh as needed

GUI Error Handling
~~~~~~~~~~~~~~~~~~

The GUI includes error handling with user-friendly dialogs:

-  **Configuration errors** automatically redirect to the Config tab
   with specific error messages
-  **File not found errors** provide clear guidance on fixing file paths
-  **Data format errors** help identify spreadsheet formatting issues
-  **Validation errors** highlight specific fields that need correction

CLI and GUI Integration
~~~~~~~~~~~~~~~~~~~~~~~

The GUI and CLI tools work seamlessly together:

-  **Shared configuration**: Both use the same
   ``~/.mmm_savings_rate/db.json`` file
-  **CLI commands work**: Use ``sr-show-config``,
   ``sr-validate-config``, etc. alongside the GUI
-  **Plot compatibility**: GUI and CLI generate identical Bokeh plots
-  **No conflicts**: You can switch between GUI and CLI freely

Requirements
------------

This utility requires **Python 3.10 or higher** (tested on Python 3.10,
3.11, and 3.12). All additional dependencies should be automatically
downloaded and included during installation.

Dependencies
~~~~~~~~~~~~

-  **Runtime dependencies**: See
   `requirements.txt <https://github.com/bbusenius/MMM_Savings_Rate/blob/master/requirements.txt>`__
-  **Development dependencies**: See
   `requirements-dev.txt <https://github.com/bbusenius/MMM_Savings_Rate/blob/master/requirements-dev.txt>`__
   (includes linting tools: flake8, black, isort)
-  **Build configuration**: See
   `pyproject.toml <https://github.com/bbusenius/MMM_Savings_Rate/blob/master/pyproject.toml>`__

Development
-----------

Documentation
~~~~~~~~~~~~~

This project uses Sphinx to generate documentation hosted on `Read the
Docs <https://mmm-savings-rate.readthedocs.io/>`__.

The documentation is automatically generated from this README file. To
update the documentation:

**Prerequisites:** - Install
`pandoc <https://pandoc.org/installing.html>`__ for converting Markdown
to reStructuredText

**Process:** 1. **Update this README.md** with any changes 2. **Convert
to Sphinx format**:
``bash    cd docs    make update-readme  # Converts README.md to index.rst using pandoc    make html          # Builds the documentation (optional - for local preview)``

The documentation will automatically rebuild on Read the Docs when
changes are pushed to the repository.

Running tests
~~~~~~~~~~~~~

This project uses a modern Python package structure with source code in
``src/``. The recommended way to run tests is using Briefcase, which
handles the package environment correctly.

**Recommended: Using Briefcase**

.. code:: bash

   # Install briefcase if not already installed
   pip install briefcase

   # Run tests with proper package setup
   briefcase dev --test

**Alternative: Using pytest**

.. code:: bash

   # Install pytest and run tests
   pip install pytest
   pytest tests/ -v

**Note**: The GitHub Actions workflow uses pytest for CI (core
dependencies only), while local development can use Briefcase for full
testing.

Code Quality and Linting
~~~~~~~~~~~~~~~~~~~~~~~~

This project uses automated code formatting and linting:

.. code:: bash

   # Install development dependencies
   pip install -r requirements-dev.txt

   # Check code formatting
   black --check .

   # Format code automatically
   black .

   # Check import sorting
   isort --check-only .

   # Fix import sorting
   isort .

   # Run linting
   flake8 .

   # Run all checks (same as CI)
   flake8 . && black --check . && isort --check-only .

Adding Enemies to db.json
~~~~~~~~~~~~~~~~~~~~~~~~~

To add an enemy for competitive plotting, edit ``db.json`` by adding
entries to the ``enemy_settings`` and ``users`` tables. Ensure the
``_id`` is unique and matches between tables. Example:

.. code:: json

   "enemy_settings": [
     {
       "_id": 2,
       "pay": "/path/to/your/income-joe.xlsx",
       "pay_date": "Date",
       "gross_income": "Gross Pay",
       "employer_match": "Employer Match",
       "taxes_and_fees": ["Federal Tax", "State Tax"],
       "savings": "/path/to/your/savings-joe.xlsx",
       "savings_date": "Date",
       "savings_accounts": ["Savings Account"],
       "notes": "",
       "show_average": true,
       "war": "on",
       "fred_url": "https://api.stlouisfed.org/fred/series/observations?series_id=PSAVERT&file_type=json",
       "fred_api_key": "",
       "goal": null,
       "fi_number": null,
       "total_balances": "",
       "percent_fi_notes": ""
     }
   ],
   "users": [
     {"_id": 1, "name": "User", "config_ref": "main_user_settings"},
     {"_id": 2, "name": "Joe", "config_ref": "enemy_2"}
   ]

Ensure the ``config_ref`` in ``users`` (e.g., “enemy_2”) uniquely
identifies the enemy’s settings in ``enemy_settings``.

**Warning**: Maintain JSON validity during manual edits. Use
``sr-validate-config`` to check for errors.
