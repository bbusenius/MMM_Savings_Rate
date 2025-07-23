MMM Savings Rate
================

MMM Savings Rate is a tool that allows users to calculate and track
their monthly savings rates over time. It was developed using functions
from the `FI module <https://github.com/bbusenius/FI>`__ and plots
savings rates using `Bokeh <https://bokeh.org/>`__.

**Key Features:** - Parse Excel (.xlsx) and CSV spreadsheets with
flexible column mapping - Interactive web-based visualizations with
Bokeh - JSON-based configuration using TinyDB for easy management - CLI
commands for configuration management - Optional FRED integration for US
average savings rate comparison - “Enemy” mode for competitive savings
rate tracking - Python 3.10+ support with automated code quality checks

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

For users
~~~~~~~~~

::

   pip install git+https://github.com/bbusenius/MMM_Savings_Rate.git#egg=mmm_savings_rate

For developers
~~~~~~~~~~~~~~

.. code:: bash

   # Clone and install in development mode
   git clone https://github.com/bbusenius/MMM_Savings_Rate.git
   cd MMM_Savings_Rate
   pip install -e .

   # Install development dependencies for linting
   pip install -r requirements-dev.txt

Or install directly from GitHub:

.. code:: bash

   pip install -e git+https://github.com/bbusenius/MMM_Savings_Rate.git#egg=mmm_savings_rate

Setting up the application
--------------------------

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

You can manage your configuration in two ways:

**Option 1: CLI Commands (Recommended)**

.. code:: bash

   # View current configuration
   sr-show-config

   # Update a setting
   sr-update-setting main_user_settings pay "/path/to/income.xlsx"
   sr-update-setting main_user_settings savings "/path/to/savings.xlsx"

   # Validate configuration
   sr-validate-config

**Option 2: Direct JSON Editing** You can directly edit the
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
worth.

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

The ``savingsrates`` command supports the following options:

-  ``-u, --user USER_ID`` - Specify which user to analyze (default: 1)
-  ``-o, --output OUTPUT_PATH`` - Specify where to save the HTML plot
   file (default: savings-rates.html)

..

   **Note:** The ``--output`` option is designed to support future
   graphical application development while maintaining full CLI
   compatibility. This allows the same core functionality to be used in
   both command-line and GUI contexts.

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

.. code:: bash

   python -m unittest discover tests -p 'test_*.py'

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
