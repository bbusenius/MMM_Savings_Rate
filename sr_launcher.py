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

from savings_rate import Plot, SavingsRate, SRConfig


def run():
    """
    Run the application.

    Args:
        config_path: string, path to a directory of config
        .ini files. Should include a trailing "/".
    """
    # Capture commandline arguments. prog='' argument must
    # match the command name in setup.py entry_points
    parser = argparse.ArgumentParser(prog='savingsrates')
    parser.add_argument('-p', nargs='?', help='A path to a directory of config files.')
    args = parser.parse_args()
    inputs = {'p': args.p}
    config_path = inputs['p']

    # Instantiate a savings rate config object
    config = SRConfig(config_path, 'config.ini')

    # Instantiate a savings rate object for a user
    savings_rate = SavingsRate(config)
    monthly_rates = savings_rate.get_monthly_savings_rates()

    # Plot the user's savings rate
    user_plot = Plot(savings_rate)
    user_plot.plot_savings_rates(monthly_rates)
