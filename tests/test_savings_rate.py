import unittest
from savings_rate import SRConfig, SavingsRate, Plot

class test_savings_rate_methods(unittest.TestCase):
    """
    Tests for individual methods.
    """
    def test_clean_num(self):
        config = SRConfig('ini', 'tests/test_config/', 'config-test.ini')
        sr = SavingsRate(config)

        val1 = sr.clean_num('')
        val2 = sr.clean_num('     ')
        val3 = sr.clean_num(None)

        self.assertRaises(TypeError, sr.clean_num, 'Son of Mogh')
        self.assertRaises(TypeError, sr.clean_num, '4.4')
        self.assertEqual(val1, 0.0), 'An empty string should evaluate to 0.0. It evaluated to ' + str(val1)
        self.assertEqual(val2, 0.0), 'An empty string should evaluate to 0.0. It evaluated to ' + str(val2)
        self.assertEqual(val3, 0.0), 'None should evaluate to 0.0. It evaluated to ' + str(val3)

