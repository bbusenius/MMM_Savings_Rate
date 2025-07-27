"""
Test that GUI and CLI plot generation produce identical results.
"""

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from mmm_savings_rate.savings_rate import Plot, SavingsRate, SRConfig


class TestGUICliPlotConsistency(unittest.TestCase):
    """Test that GUI and CLI plots are identical."""

    def setUp(self):
        """Set up test fixtures."""
        # Create temporary directories for test output and config
        self.temp_dir = tempfile.mkdtemp()
        self.temp_config_dir = tempfile.mkdtemp()
        self.cli_output_path = os.path.join(self.temp_dir, 'cli_plot.html')
        self.gui_output_path = os.path.join(self.temp_dir, 'gui_plot.html')

        # Get absolute paths to test data files
        project_root = Path(__file__).parent.parent
        csv_income_path = project_root / "csv" / "income-example.csv"
        csv_savings_path = project_root / "csv" / "savings-example.csv"

        # Create test database configuration
        self.test_db_path = Path(self.temp_config_dir) / "test_config.json"
        test_config = {
            "main_user_settings": {
                "pay": str(csv_income_path),
                "pay_date": "Date",
                "gross_income": "Gross Pay",
                "employer_match": "Employer Match",
                "taxes_and_fees": ["OASDI", "Medicare"],
                "savings": str(csv_savings_path),
                "savings_date": "Date",
                "savings_accounts": ["Scottrade", "Vanguard 403b", "Vanguard Roth"],
                "notes": "Test notes",
                "show_average": True,
                "war": "off",
                "fred_url": "",
                "fred_api_key": "",
                "goal": 50.0,
                "fi_number": 1000000.0,
                "total_balances": False,
                "percent_fi_notes": "",
            },
            "users": [
                {"_id": 1, "name": "TestUser", "config_ref": "main_user_settings"}
            ],
            "enemy_settings": [],
        }

        with open(self.test_db_path, 'w') as f:
            json.dump(test_config, f, indent=2)

    def tearDown(self):
        """Clean up test fixtures."""
        # Clean up temporary files and directories
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
        if os.path.exists(self.temp_config_dir):
            shutil.rmtree(self.temp_config_dir)

    @mock.patch('mmm_savings_rate.savings_rate.requests.get')
    def test_cli_gui_plot_identical(self, mock_get):
        """Test that CLI and GUI produce identical HTML plots."""
        # Mock FRED API response to avoid network dependency
        mock_response = mock.Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'observations': []}
        mock_get.return_value = mock_response

        # Create test configuration using test database
        config = SRConfig(test=True, test_file=str(self.test_db_path), user_id=1)

        try:
            # Create SavingsRate instance
            savings_rate = SavingsRate(config)

            # Mock the monthly rates calculation to return consistent test data
            test_monthly_rates = [
                ('2024-01-01', 30.0, ['Test note 1'], None, ''),
                ('2024-02-01', 32.0, ['Test note 2'], None, ''),
            ]

            with mock.patch.object(
                savings_rate,
                'get_monthly_savings_rates',
                return_value=test_monthly_rates,
            ):

                # Create Plot instance
                user_plot = Plot(savings_rate)

                # Generate CLI plot (embed=False)
                user_plot.plot_savings_rates(
                    test_monthly_rates,
                    embed=False,
                    output_path=self.cli_output_path,
                    no_browser=True,
                )

                # Generate GUI plot (embed=True with output_path)
                user_plot.plot_savings_rates(
                    test_monthly_rates, embed=True, output_path=self.gui_output_path
                )

                # Verify both files were created
                self.assertTrue(
                    os.path.exists(self.cli_output_path),
                    "CLI plot file was not created",
                )
                self.assertTrue(
                    os.path.exists(self.gui_output_path),
                    "GUI plot file was not created",
                )

                # Read and compare HTML content
                with open(self.cli_output_path, 'r', encoding='utf-8') as f:
                    cli_html = f.read()

                with open(self.gui_output_path, 'r', encoding='utf-8') as f:
                    gui_html = f.read()

                # Verify files are not empty
                self.assertGreater(len(cli_html), 1000, "CLI HTML file seems too small")
                self.assertGreater(len(gui_html), 1000, "GUI HTML file seems too small")

                # Compare HTML content - they should be functionally identical
                # Note: Bokeh generates unique IDs, so we need to normalize those
                import re

                def normalize_bokeh_html(html_content):
                    """Normalize Bokeh-generated HTML by replacing dynamic IDs."""
                    # Replace UUID patterns
                    uuid_pattern = (
                        r'[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}'
                    )
                    content = re.sub(uuid_pattern, 'UUID_PLACEHOLDER', html_content)

                    # Replace p-element IDs (p1003, p1112, etc.)
                    p_id_pattern = r'p\d+'
                    content = re.sub(p_id_pattern, 'P_ID_PLACEHOLDER', content)

                    return content

                cli_normalized = normalize_bokeh_html(cli_html)
                gui_normalized = normalize_bokeh_html(gui_html)

                # Compare normalized content
                self.assertEqual(
                    cli_normalized,
                    gui_normalized,
                    "CLI and GUI plots should generate functionally identical HTML output",
                )

                # Verify responsive sizing is present in both
                self.assertIn(
                    'stretch_both', cli_html, "CLI plot should have responsive sizing"
                )
                self.assertIn(
                    'stretch_both', gui_html, "GUI plot should have responsive sizing"
                )

                # Verify plot contains expected data points
                self.assertIn(
                    '30.0', cli_html, "CLI plot should contain test data point"
                )
                self.assertIn(
                    '30.0', gui_html, "GUI plot should contain test data point"
                )
                self.assertIn(
                    '32.0', cli_html, "CLI plot should contain test data point"
                )
                self.assertIn(
                    '32.0', gui_html, "GUI plot should contain test data point"
                )

        finally:
            # Clean up config
            if hasattr(config, 'close'):
                config.close()

    @mock.patch('mmm_savings_rate.savings_rate.requests.get')
    def test_plot_sizing_mode_consistency(self, mock_get):
        """Test that both CLI and GUI plots have responsive sizing."""
        # Mock FRED API response
        mock_response = mock.Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'observations': []}
        mock_get.return_value = mock_response

        # Create test configuration using test database
        config = SRConfig(test=True, test_file=str(self.test_db_path), user_id=1)

        try:
            savings_rate = SavingsRate(config)
            test_monthly_rates = [('2024-01-01', 30.0, ['Note'], None, '')]

            with mock.patch.object(
                savings_rate,
                'get_monthly_savings_rates',
                return_value=test_monthly_rates,
            ):
                user_plot = Plot(savings_rate)

                # Test CLI path
                user_plot.plot_savings_rates(
                    test_monthly_rates,
                    embed=False,
                    output_path=self.cli_output_path,
                    no_browser=True,
                )

                # Test GUI path
                user_plot.plot_savings_rates(
                    test_monthly_rates, embed=True, output_path=self.gui_output_path
                )

                # Check both files contain responsive sizing
                with open(self.cli_output_path, 'r') as f:
                    cli_content = f.read()

                with open(self.gui_output_path, 'r') as f:
                    gui_content = f.read()

                # Both should contain stretch_both sizing mode for responsiveness
                self.assertIn(
                    'stretch_both', cli_content, "CLI plot must have responsive sizing"
                )
                self.assertIn(
                    'stretch_both', gui_content, "GUI plot must have responsive sizing"
                )

        finally:
            # Clean up config
            if hasattr(config, 'close'):
                config.close()


if __name__ == '__main__':
    unittest.main()
