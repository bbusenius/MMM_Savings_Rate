# -*- coding: utf-8 -*-
from setuptools import setup, find_packages

setup(
    name='MMM_Savings_Rate',
    description='An application that can parse spreadsheets in order to ' \
                'calculate and plot a user\'s monthly savings rate over time. ',
    version='0.1',
    author='Brad Busenius',
    packages = find_packages(),
    py_modules=[
        'savings_rate', 
    ], 
    url='https://github.com/bbusenius/MMM_Savings_Rate.git',
    license='GNU GPLv3',
    install_requires=[
        'bokeh',
    ],
    #test_suite='tests',
    zip_safe=False
)

