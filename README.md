# MMM_Savings_Rate

This application is a command-line utility that allows users to calculate and track their monthly savings rates over time. Users simply enter their savings and income data into a spreadsheet saved as a .csv. Unique spreadsheet column headers are mapped to the application through user configuration files, allowing the utility to be used with any custom spreadsheet. When the simulation is run, user monthly savings rates are plotted on a line graph.

![Example savings rates plotted](https://github.com/bbusenius/MMM_Savings_Rate/raw/master/docs/screenshot.png)

Additionally, users may supply secondary, "enemy" spreadsheets. This feature is provided in order to make the experience fun, game-like, and competitive for those who prefer such an experience. If an enemy spreadsheet is provided, the enemy savings rates are plotted alongside those of the user. This feature might be used by spouses who wish to compete with each other, for example.

*MMM_Savings_Rate was inspired by Mr. Money Mustache. Visit the Mr. Money Mustache website and [read this article to learn more](http://www.mrmoneymustache.com/2012/01/13/the-shockingly-simple-math-behind-early-retirement).*

## Web version
Though MMM_Savings_Rate is meant to be run from the command-line, a full, graphical, web-based version of the project exists at: https://savingsratewars.com/. Use the web-based version of the software if you don't want to deal with installation and configuration.


## Installation
This package should generally be installed using pip.

### For users 

```
pip install MMM-Savings-Rate
```
### For developers

```
git clone https://github.com/bbusenius/MMM_Savings_Rate.git
python3 setup.py develop 
```
or 

```
pip install -e git+https://github.com/bbusenius/MMM_Savings_Rate.git#egg=mmm_savings_rate
```
## Using the application

In order to get things going, you'll only need to take the following steps:

1. Setup a directory of .csv files with the financial data needed to run the simulation.
2. Configuration:
  - Create an account-config.ini with player information.
  - Create a config.ini with personal settings and column mappings.
3. Run the simulation command with a path to your configuration files. 

Read on to see how to do each of these things.

### Spreadsheet files
MMM_Savings_Rate was designed to be flexible in order to work with your preexisting spreadsheets. At the moment, spreadsheets must be saved as .csv files, however, column headers can be unique, so it doesn't matter what labels you use to categorize things. To get started you'll need financial data for both **income** and **savings**.

This data can exist in a single spreadsheet with a variety of financial data or separate spreadsheets for income and savings. How you set it up is up to you, however, certain data is required. The application will allow you to map your column labels to fields, so you don't have to name them the same as outlined here. You also might want to split some of these fields over multiple columns in your spreadsheet. Jump to the configuration section to learn how to do this. In any event, however you decide to enter the data in your spreadsheet, all of the following fields must be represented in some fashion. 

- **Date for pay** - the date of your paycheck or date associated with the income being entered. The application can parse most date formats. 
- **Gross Pay** - the amount of money you made in its entirety before taxes were withdrawn.
- **Employer Match** - money contributed to a retirement plan by your employer.
- **Taxes and Fees** - any taxes and fees taken out of your paycheck before it was delivered, e.g. OASDI, Medicare, etc.
- **Savings Accounts** - a dollar amount (mapped to 1 or multiple accounts)
- **Date for savings** - the date you saved money into each account.

*Note about "Savings Accounts": you might have multiple savings accounts, e.g. Bank Account, Vanguard Brokerage, Roth. Each one of these would contain a dollar amount representing the quantity of money saved for the month. Mapping will be handled in the configuration stage.*

[For example spreadsheets please look in the csv directory](https://github.com/bbusenius/MMM_Savings_Rate/tree/master/csv). This should give you a good idea of how to lay things out. 

### Configuration

In order to run the simulation the following two files are required:

1. account-config.ini - the configuration for the players. Think of this as a listing of users. Each user has an id, name, and a link to his or her personal configuration.
2. config.ini - the configuration for the main user. Think of this as all of your personal settings.

*Optional, "enemy" config files can be named however you like, e.g. config-spouse.ini. These should be setup in a similar fashion as config.ini and they should be listed as pipe separated groupings under "enemies" in account-config.ini.*

#### account-config.ini
A file must exist with the name account-config.ini. An example account-config.ini might look like this:

```
[Users]
; Unique ID, name, and config file name for user.
self = 1,My name,config.ini

; Unique ID, name, and pipe separated list of config 
; file names for user's enemies.
enemies = 2,Joe,config-spouse.ini|3,Brother,config-brother.ini
```

The [Users] section is required. The "self" field represents the main player (you). This field should contain a comma separated list with a unique numerical ID, followed by a name, and the name of a main user config file.
 
The "enemies" field is optional. If it's being used, it should be setup the same as the self field, however, if more than one enemy exists, this can be a pipe separated list of comma separated values.

#### config.ini
The config.ini file is the second configuration file. This file is required. It contains all of your personal settings and spreadsheet mappings. 

[Please look at this example](https://github.com/bbusenius/MMM_Savings_Rate/blob/master/config/config-example.ini).

The majority of what's here is listed under [Sources]. Settings include:

- **pay** - a full path to your income .csv file.
- **pay_date** - the name of a column header for the dates of income or pay transactions.
- **savings** - a full path to your savings .csv file (can be the same file used for pay).
- **savings_date** - the name of a column header for the dates of income or pay transactions.
- **gross_income** - the name of a column header in your spreadsheet that represents gross pay.
- **employer_match** - the name of a column header in your spreadsheet that represents your employer match.
- **taxes_and_fees** - the names of column headers in your spreadsheet that contain taxes and fees.
- **savings_accounts** - the names of column headers in your spreadsheet that contain savings data from an account or accounts.
- **war** - allows you to show or hide, "enemy" plots on your graph. Set this to, "off" if you only want to see your own data.

Settings under [Graph] allow you to change the size of the plot that's generated. 
*Note: Mint integration is not yet operational*.

### Running the simulation

Once you have your .csv and your config files ready to go, you can run the application. Just open a terminal and type the command:

```
savingsrates -p /home/joeconsumer/Documents/Code/Projects/MMM_Savings_Rate/config/
```
The -p flag should specify the full path to your directory of config files. When you run the command a plot of your monthly savings rates should open in a browser window.

## Requirements
This utility runs on python 3.4. All additional dependencies should be automatically downloaded and included during installation. If you'd like to see all of what will be installed look at [setup.py](https://github.com/bbusenius/MMM_Savings_Rate/blob/master/setup.py) or [requirements.txt](https://github.com/bbusenius/MMM_Savings_Rate/blob/master/requirements.txt).
