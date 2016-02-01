# -*- coding: utf-8 -*-
from setuptools import setup, find_packages

try:
    import pypandoc
    LONG_DESCRIPTION = pypandoc.convert('README.md', 'rst')
except(IOError, ImportError):
    LONG_DESCRIPTION = open('README.md').read()

setup(
    name='MMM_Savings_Rate',
    description='An application that can parse spreadsheets in order to ' \
                'calculate and plot a user\'s monthly savings rate over time. ',
    version='0.3',
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
    test_suite='tests',
    long_description=LONG_DESCRIPTION,
    zip_safe=False
)

