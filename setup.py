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
        'sr_launcher', 
    ], 
    url='https://github.com/bbusenius/MMM_Savings_Rate.git',
    license='GNU GPLv3, see LICENCE.txt',
    include_package_data=True,
    install_requires=[
        'bokeh',
        'certifi',
        'keyring',
        'mintapi',
        'python-dateutil',
    ],
    dependency_links=[
        "git+https://github.com/bbusenius/Diablo-Python.git#egg=diablo_python",
    ],
    #test_suite='tests',
    zip_safe=False
)

