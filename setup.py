# -*- coding: utf-8 -*-
from setuptools import find_packages, setup

with open('README.md', 'r', encoding='utf-8') as fh:
    long_description = fh.read()
    long_description_type = 'text/markdown'

try:
    import pypandoc

    long_description = pypandoc.convert_text(long_description, 'rst', format='md')
    long_description_type = 'text/x-rst'
except (IOError, ImportError):
    pass

setup(
    name='MMM_Savings_Rate',
    description='An application that can parse spreadsheets in order to '
    'calculate and plot a user\'s monthly savings rate over time. ',
    python_requires='>=3.10',
    version='1.0',
    author='Brad Busenius',
    author_email='bbusenius@gmail.com',
    packages=find_packages(),
    scripts=[
        'sr_launcher.py',
    ],
    py_modules=[
        'savings_rate',
    ],
    entry_points={
        'console_scripts': [
            'savingsrates = sr_launcher:run',
        ],
    },
    url='https://github.com/bbusenius/MMM_Savings_Rate.git',
    license='GNU GPLv3, see LICENSE.txt',
    include_package_data=True,
    install_requires=[
        'bokeh',
        'diablo_python @ git+https://github.com/bbusenius/Diablo-Python.git#egg=diablo_python',
        'fi @ git+https://github.com/bbusenius/FI.git#egg=FI',
        'openpyxl',
        'pandas',
        'python-dateutil',
        'requests',
    ],
    test_suite='tests',
    long_description=long_description,
    long_description_content_type=long_description_type,
    zip_safe=False,
)
