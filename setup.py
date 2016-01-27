# -*- coding: utf-8 -*-
from setuptools import setup, find_packages

setup(
    name='MMM_Savings_Rate',
    description='An application that can parse spreadsheets in order to ' \
                'calculate and plot a user\'s monthly savings rate over time. ',
    version='0.2',
    author='Brad Busenius',
    author_email='bbusenius@gmail.com',
    packages = find_packages(),
    scripts=[
        'sr_launcher.py',
    ],
    py_modules=[
        'savings_rate',
    ],
    entry_points = {
        'console_scripts': [
            'savingsrates = sr_launcher:run',                  
        ],              
    },
    url='https://github.com/bbusenius/MMM_Savings_Rate.git',
    license='GNU GPLv3, see LICENSE.txt',
    include_package_data=True,
    install_requires=[
        'bokeh',
        'certifi',
        'diablo-python',
        'keyring',
        'mintapi',
        'python-dateutil',
    ],
    #test_suite='tests',
    zip_safe=False
)

