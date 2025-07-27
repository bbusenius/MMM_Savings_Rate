"""
MMM Savings Rate - Personal finance application for tracking savings rates
"""

from .gui import MMMSavingsRateApp


def main():
    return MMMSavingsRateApp('MMM Savings Rate', 'com.savingsratewars')


if __name__ == '__main__':
    app = main()
    app.main_loop()
