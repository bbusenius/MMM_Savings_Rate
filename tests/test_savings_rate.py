import unittest
import configparser
from savings_rate import SRConfig, SavingsRate, Plot, REQUIRED_INI_ACCOUNT_OPTIONS, REQUIRED_INI_USER_OPTIONS
from decimal import *
from collections import OrderedDict
import sys

class test_savings_rate(unittest.TestCase):
    """
    Tests for individual methods.
    """
    def test_clean_num(self):
        config = SRConfig('ini', 'tests/test_config/', 'config-test.ini')
        sr = SavingsRate(config)

        val1 = sr.clean_num('')
        val2 = sr.clean_num('     ')
        val3 = sr.clean_num(None)
        val4 = sr.clean_num(4)
        val5 = sr.clean_num(4.4)
        val6 = sr.clean_num(Decimal(4.4))

        self.assertRaises(TypeError, sr.clean_num, 'Son of Mogh')
        self.assertRaises(TypeError, sr.clean_num, '4.4')
        self.assertEqual(val1, 0.0), 'An empty string should evaluate to 0.0. It evaluated to ' + str(val1)
        self.assertEqual(val2, 0.0), 'An empty string should evaluate to 0.0. It evaluated to ' + str(val2)
        self.assertEqual(val3, 0.0), 'None should evaluate to 0.0. It evaluated to ' + str(val3)
        self.assertEqual(val4, 4), '4 should evaluate to 4.4. It evaluated to ' + str(val4)
        self.assertEqual(val5, 4.4), '4.4 should evaluate to 4.4. It evaluated to ' + str(val5)
        self.assertEqual(val6, Decimal(4.4)), '4.4 should evaluate to Decimal(4.4). It evaluated to ' + str(val6)


    def test_spreadsheet_with_misconfigured_income_columns(self):
        """
        Test a spreadsheet that doesn't have the column
        headers that were set in config.ini. Having a required
        field set in the config.ini that doesn't exist in the
        corresponding .csv, should throw an assertion error.
        """
        config = SRConfig('ini', 'tests/test_config/', 'config-test.ini')
        config.required_income_columns = set(['Foo', 'Bar'])
        self.assertRaises(AssertionError, SavingsRate, config)


    def test_spreadsheet_with_misconfigured_savings_columns(self):
        """
        Test a spreadsheet that doesn't have the column
        headers that were set in config.ini. Having a required
        field set in the config.ini that doesn't exist in the
        corresponding .csv, should throw an assertion error.
        """
        config = SRConfig('ini', 'tests/test_config/', 'config-test.ini')
        config.required_savings_columns = config.required_savings_columns.union(set(['Additional Heading']))
        self.assertRaises(AssertionError, SavingsRate, config)  


    def test_data_loaded_by_load_pay_from_csv (self):
        """
        Dates should be in chronological order assuming
        they were entered that way. All required_income_columns
        should be present in the data structure.
        """
        config = SRConfig('ini', 'tests/test_config/', 'config-test.ini')
        sr = SavingsRate(config)
        
        dates = []
        i = 0
        for d in sr.income:
            for req in sr.config.required_income_columns:
                self.assertEqual(req in sr.income[d], True, \
                    'Missing a field in SavingsRate.income.')
            dates.append(d)
            if i > 0:
                assert d > dates[i-1], \
                    'Income transaction dates are not in chronological order. Were they entered chronologically?'
            i += 1


    def test_data_loaded_by_load_savings_from_csv(self):
        """
        Dates should be in chronological order assuming
        they were entered that way. All required_income_columns
        should be present in the data structure.
        """
        config = SRConfig('ini', 'tests/test_config/', 'config-test.ini')
        sr = SavingsRate(config)
        
        dates = []
        i = 0
        for d in sr.savings:
            for req in sr.config.required_savings_columns:
                self.assertEqual(req in sr.savings[d], True, \
                    'Missing a field in SavingsRate.savings.')
            dates.append(d)
            if i > 0:
                assert d > dates[i-1], \
                    'Income transaction dates are not in chronological order. Were they entered chronologically?'
            i += 1


    def test_empty_csv_files(self):
        """
        The files exist with the proper column headings
        but they don't have any rows populated. This 
        shouldn't blow up.
        """
        config = SRConfig('ini', 'tests/test_config/', 'config-test-empty-csv.ini', \
            test=True, test_file='account-config-empty-csv.ini')
        sr = SavingsRate(config)

        self.assertEqual(sr.income, OrderedDict())
        self.assertEqual(sr.savings, OrderedDict())


    def test_blank_csv_files(self):
        """
        The files exist but they are totally blank.
        PROBLEM - this test shouldn't pass but it does.
        At a minimum, test_columns should throw an 
        AssertionError, shouldn't it? What's going on here?
        """
        config = SRConfig('ini', 'tests/test_config/', 'config-test-blank-csv.ini', \
            test=True, test_file='account-config-blank-csv.ini')
        sr = SavingsRate(config)


    def test_get_taxes_from_csv(self):
        """
        There should be as many items as commas in 
        the config +1.
        """
        config = SRConfig('ini', 'tests/test_config/', 'config-test.ini')
        sr = SavingsRate(config)
        commas_in_config = config.user_config.get('Sources', 'taxes_and_fees').count(',') 
        self.assertEqual(len(sr.get_taxes_from_csv()), commas_in_config + 1)


    def test_get_monthly_savings_rates_50_50(self):
        """
        %50 SR each month, %50 average
        """
        config = SRConfig('ini', 'tests/test_config/', 'config-test.ini')
        sr = SavingsRate(config)

        md1 = OrderedDict()
        md1['2015-01'] = {'income' : [Decimal(2000.0)],
                          'employer_match' : [Decimal(200.0)],
                          'taxes_and_fees' : [Decimal(200.0)],
                          'savings' : [Decimal(1000.0)]}
        md1['2015-02'] = {'income' : [Decimal(2000.0)],
                          'employer_match' : [Decimal(200.0)],
                          'taxes_and_fees' : [Decimal(200.0)],
                          'savings' : [Decimal(1000.0)]}

        r1 = sr.get_monthly_savings_rates(test_data=md1)
        for item1 in r1:
            self.assertEqual(item1[1], Decimal(50.0), \
                'Incorrect savings rate. Calculated: ' + str(item1[1]))
        average_rates = sr.average_monthly_savings_rates(r1)
        self.assertEqual(average_rates, Decimal(50.0), \
            'Wrong average for monthly rates.')


    def test_get_monthly_savings_rates_100_100(self):
        """
        %100 SR each month, %100 average
        """
        config = SRConfig('ini', 'tests/test_config/', 'config-test.ini')
        sr = SavingsRate(config)

        md2 = OrderedDict()
        md2['2015-01'] = {'income' : [Decimal(2000.0)],
                          'employer_match' : [Decimal(200.0)],
                          'taxes_and_fees' : [Decimal(200.0)],
                          'savings' : [Decimal(2000.0)]}
        md2['2015-02'] = {'income' : [Decimal(2000.0)],
                          'employer_match' : [Decimal(200.0)],
                          'taxes_and_fees' : [Decimal(200.0)],
                          'savings' : [Decimal(2000.0)]}

        r2 = sr.get_monthly_savings_rates(test_data=md2)
        for item2 in r2:
            self.assertEqual(item2[1], Decimal(100.0), \
                'Incorrect savings rate. Calculated: ' + str(item2[1]))
        average_rates = sr.average_monthly_savings_rates(r2)
        self.assertEqual(average_rates, Decimal(100.0), \
            'Wrong average for monthly rates.')


    def test_get_monthly_savings_rates_25_75(self):
        """
        %25 SR first month, %75 second month, %50 average
        """
        config = SRConfig('ini', 'tests/test_config/', 'config-test.ini')
        sr = SavingsRate(config)

        md3 = OrderedDict()
        md3['2015-01'] = {'income' : [Decimal(2000.0)],
                          'employer_match' : [Decimal(200.0)],
                          'taxes_and_fees' : [Decimal(200.0)],
                          'savings' : [Decimal(500.0)]}
        md3['2015-02'] = {'income' : [Decimal(2000.0)],
                          'employer_match' : [Decimal(200.0)],
                          'taxes_and_fees' : [Decimal(200.0)],
                          'savings' : [Decimal(1500.0)]}

        r3 = sr.get_monthly_savings_rates(test_data=md3)
      
        self.assertEqual(r3[0][1], Decimal(25), \
            'Incorrect savings rate. Calculated: ' + str(r3[0][1]))
        self.assertEqual(r3[1][1], Decimal(75), \
            'Incorrect savings rate. Calculated: ' + str(r3[1][1]))
        average_rates = sr.average_monthly_savings_rates(r3)
        self.assertEqual(average_rates, Decimal(50.0), \
            'Wrong average for monthly rates.')


    def test_get_monthly_savings_rates_0_0(self):
        """
        %0 SR each month, %0 average
        """
        config = SRConfig('ini', 'tests/test_config/', 'config-test.ini')
        sr = SavingsRate(config)

        md = OrderedDict()
        md['2015-01'] = {'income' : [Decimal(0.0)],
                         'employer_match' : [Decimal(0.0)],
                         'taxes_and_fees' : [Decimal(0.0)],
                         'savings' : [Decimal(0.0)]}
        md['2015-02'] = {'income' : [Decimal(0.0)],
                         'employer_match' : [Decimal(0.0)],
                         'taxes_and_fees' : [Decimal(0.0)],
                         'savings' : [Decimal(0.0)]}

        r4 = sr.get_monthly_savings_rates(test_data=md)
        for item4 in r4:
            self.assertEqual(item4[1], Decimal(0.0), \
                'Incorrect savings rate. Calculated: ' + str(item4[1]))
        average_rates = sr.average_monthly_savings_rates(r4)
        self.assertEqual(average_rates, Decimal(0.0), \
            'Wrong average for monthly rates.')


    def test_average_monthly_savings_rates_1_month(self):
        """
        %0 SR each month, %0 average
        """
        config = SRConfig('ini', 'tests/test_config/', 'config-test.ini')
        sr = SavingsRate(config)

        md = OrderedDict()
        md['2015-01'] = {'income' : [Decimal(2000.0)],
                         'employer_match' : [Decimal(200.0)],
                         'taxes_and_fees' : [Decimal(200.0)],
                         'savings' : [Decimal(500.0)]}

        rates = sr.get_monthly_savings_rates(test_data=md)
        average_rates = sr.average_monthly_savings_rates(rates)
        self.assertEqual(average_rates, Decimal(25.0), \
            'Wrong average for monthly rates.')
