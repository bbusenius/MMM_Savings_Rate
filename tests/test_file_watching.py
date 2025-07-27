"""
Test suite for file watching functionality in MMM Savings Rate GUI.

Tests the FileWatcher class, automatic plot refresh, and config save integration.
"""

import asyncio
import os
import shutil
import tempfile
import threading
import time
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

try:
    from mmm_savings_rate.gui import FileWatcher, MMMSavingsRateApp

    GUI_AVAILABLE = True
except ImportError:
    GUI_AVAILABLE = False
    FileWatcher = None
    MMMSavingsRateApp = None


@unittest.skipIf(not GUI_AVAILABLE, "GUI dependencies not available")
class TestFileWatcher(unittest.TestCase):
    """Test the FileWatcher class functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_config_dir = tempfile.mkdtemp()

        # Create mock app
        self.mock_app = MagicMock()
        self.mock_app.plot_tab = MagicMock()

        # Create AsyncMock that returns a simple coroutine instead of another coroutine
        async def mock_refresh():
            return None

        self.mock_app.plot_tab.refresh_plot = AsyncMock(side_effect=mock_refresh)

        # Mock the event loop for threading tests
        self.mock_loop = MagicMock()
        self.mock_app._impl.loop = self.mock_loop
        self.mock_loop.is_running.return_value = True

        # Create file watcher instance
        self.file_watcher = FileWatcher(self.mock_app)

    def tearDown(self):
        """Clean up test fixtures."""
        try:
            self.file_watcher.stop()
        except Exception:
            pass

        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
        if os.path.exists(self.temp_config_dir):
            shutil.rmtree(self.temp_config_dir)

    def test_file_watcher_initialization(self):
        """Test FileWatcher initialization."""
        self.assertIsNotNone(self.file_watcher.observer)
        self.assertEqual(len(self.file_watcher.watched_files), 0)
        self.assertIsNotNone(self.file_watcher.logger)
        self.assertEqual(self.file_watcher._debounce_delay, 1.0)

    def test_watch_file_nonexistent(self):
        """Test watching a file that doesn't exist."""
        nonexistent_file = os.path.join(self.temp_dir, "nonexistent.xlsx")
        initial_count = len(self.file_watcher.watched_files)

        self.file_watcher.watch_file(nonexistent_file)

        # Should not add nonexistent file to watch list
        self.assertEqual(len(self.file_watcher.watched_files), initial_count)

    def test_watch_file_existing(self):
        """Test watching an existing file."""
        # Create a test file
        test_file = os.path.join(self.temp_dir, "test.xlsx")
        with open(test_file, 'w') as f:
            f.write("test content")

        self.file_watcher.watch_file(test_file)

        # Should add file to watch list
        abs_path = os.path.abspath(test_file)
        self.assertIn(abs_path, self.file_watcher.watched_files)

    def test_watch_file_absolute_path_conversion(self):
        """Test that relative paths are converted to absolute paths."""
        # Create a test file
        test_file = os.path.join(self.temp_dir, "test.csv")
        with open(test_file, 'w') as f:
            f.write("test content")

        # Change to temp directory and use relative path
        original_cwd = os.getcwd()
        try:
            os.chdir(self.temp_dir)
            self.file_watcher.watch_file("test.csv")

            # Should store absolute path
            abs_path = os.path.abspath("test.csv")
            self.assertIn(abs_path, self.file_watcher.watched_files)

        finally:
            os.chdir(original_cwd)

    def test_unwatch_file(self):
        """Test removing a file from watch list."""
        # Create and watch a test file
        test_file = os.path.join(self.temp_dir, "test.xlsx")
        with open(test_file, 'w') as f:
            f.write("test content")

        self.file_watcher.watch_file(test_file)
        abs_path = os.path.abspath(test_file)
        self.assertIn(abs_path, self.file_watcher.watched_files)

        # Unwatch the file
        self.file_watcher.unwatch_file(test_file)
        self.assertNotIn(abs_path, self.file_watcher.watched_files)

    def test_start_stop_observer(self):
        """Test starting and stopping the file observer."""
        # Start observer
        self.file_watcher.start()
        self.assertTrue(self.file_watcher.observer.is_alive())

        # Stop observer
        self.file_watcher.stop()
        self.assertFalse(self.file_watcher.observer.is_alive())

    @patch('mmm_savings_rate.gui.asyncio.run_coroutine_threadsafe')
    def test_execute_refresh_with_event_loop(self, mock_run_coroutine):
        """Test plot refresh execution with available event loop."""
        self.file_watcher._execute_refresh()

        # Should call asyncio.run_coroutine_threadsafe
        mock_run_coroutine.assert_called_once()
        # Verify the arguments separately due to coroutine object ID differences
        args, kwargs = mock_run_coroutine.call_args
        self.assertEqual(len(args), 2)
        self.assertEqual(args[1], self.mock_loop)

    @patch('mmm_savings_rate.gui.asyncio.get_running_loop')
    @patch('mmm_savings_rate.gui.asyncio.run_coroutine_threadsafe')
    def test_execute_refresh_fallback_loop(self, mock_run_coroutine, mock_get_loop):
        """Test plot refresh with fallback event loop detection."""
        # Mock no _impl.loop available
        self.mock_app._impl.loop = None
        fallback_loop = MagicMock()
        mock_get_loop.return_value = fallback_loop

        self.file_watcher._execute_refresh()

        # Should use fallback loop
        mock_run_coroutine.assert_called_once()
        # Verify the arguments separately due to coroutine object ID differences
        args, kwargs = mock_run_coroutine.call_args
        self.assertEqual(len(args), 2)
        self.assertEqual(args[1], fallback_loop)

    def test_debounce_timer_cancellation(self):
        """Test that rapid calls cancel previous debounce timers."""
        with patch.object(self.file_watcher, '_execute_refresh') as mock_execute:
            # Trigger multiple rapid refreshes
            self.file_watcher._trigger_refresh_debounced()
            self.file_watcher._trigger_refresh_debounced()
            self.file_watcher._trigger_refresh_debounced()

            # Wait longer than debounce delay
            time.sleep(1.2)

            # Should only execute once due to debouncing
            mock_execute.assert_called_once()

    def test_update_watched_files_with_mock_db(self):
        """Test updating watched files based on configuration."""
        # Mock database manager
        mock_db_manager = MagicMock()
        mock_settings = {
            'pay': os.path.join(self.temp_dir, 'income.xlsx'),
            'savings': os.path.join(self.temp_dir, 'savings.xlsx'),
        }

        # Create test files
        for file_path in mock_settings.values():
            with open(file_path, 'w') as f:
                f.write("test content")

        mock_db_manager.get_main_user_settings.return_value = mock_settings
        self.mock_app.db_manager = mock_db_manager

        # Update watched files
        self.file_watcher.update_watched_files()

        # Should watch both files
        self.assertEqual(len(self.file_watcher.watched_files), 2)
        for file_path in mock_settings.values():
            abs_path = os.path.abspath(file_path)
            self.assertIn(abs_path, self.file_watcher.watched_files)


@unittest.skipIf(not GUI_AVAILABLE, "GUI dependencies not available")
class TestFileWatchingIntegration(unittest.TestCase):
    """Test file watching integration with GUI components."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_config_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test fixtures."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
        if os.path.exists(self.temp_config_dir):
            shutil.rmtree(self.temp_config_dir)

    @patch('mmm_savings_rate.gui.asyncio.create_task')
    def test_app_initializes_file_watcher(self, mock_create_task):
        """Test that the main app initializes file watcher on startup."""
        with patch('mmm_savings_rate.gui.DBConfigManager') as mock_db_class:
            mock_db = MagicMock()
            mock_db.initialize_db.return_value = True
            mock_db.get_main_user_settings.return_value = {'pay': '', 'savings': ''}
            mock_db_class.return_value = mock_db

            # Create app instance
            app = MMMSavingsRateApp('Test App', 'com.test')
            app.startup()

            # Should have file watcher
            self.assertIsNotNone(app.file_watcher)
            self.assertIsInstance(app.file_watcher, FileWatcher)


@unittest.skipIf(not GUI_AVAILABLE, "GUI dependencies not available")
class TestConfigSaveAutoRefresh(unittest.TestCase):
    """Test automatic plot refresh when config is saved."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test fixtures."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_save_config_triggers_plot_refresh(self):
        """Test that saving config triggers both file watcher update and plot refresh."""
        # Create mock app and config tab
        mock_app = MagicMock()
        mock_app.plot_tab = MagicMock()
        mock_app.plot_tab.refresh_plot = AsyncMock()
        mock_app.file_watcher = MagicMock()
        mock_app.db_manager = MagicMock()
        mock_app.main_window = MagicMock()
        mock_app.main_window.dialog = AsyncMock()

        # Mock successful config save
        mock_app.db_manager.update_setting.return_value = True

        # Import ConfigTab here to avoid import issues
        from mmm_savings_rate.gui import ConfigTab

        with patch.object(ConfigTab, '_load_config_values'):
            config_tab = ConfigTab(mock_app)

            # Mock form values
            with patch.object(config_tab, '_get_form_values') as mock_get_values:
                mock_get_values.return_value = {
                    'pay': '/test/income.xlsx',
                    'savings': '/test/savings.xlsx',
                }

                # Use asyncio.run to properly handle the async call
                # Avoid GLib event loop conflicts by using new thread
                result = None
                exception = None

                def run_async():
                    nonlocal result, exception
                    try:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        result = loop.run_until_complete(config_tab.save_config(None))
                        loop.close()
                    except Exception as e:
                        exception = e

                thread = threading.Thread(target=run_async)
                thread.start()
                thread.join()

                # Threading exceptions aren't always forwarded to the main thread
                # Make sure the test fails if it should
                if exception:
                    raise exception

                # Should update file watcher
                mock_app.file_watcher.update_watched_files.assert_called_once()

                # Should refresh plot
                mock_app.plot_tab.refresh_plot.assert_called_once()

                # Should show success dialog
                mock_app.main_window.dialog.assert_called_once()

    def test_save_config_handles_errors(self):
        """Test that config save errors are handled properly."""
        # Create mock app and config tab
        mock_app = MagicMock()
        mock_app.plot_tab = MagicMock()
        mock_app.plot_tab.refresh_plot = AsyncMock()
        mock_app.file_watcher = MagicMock()
        mock_app.db_manager = MagicMock()
        mock_app.main_window = MagicMock()
        mock_app.main_window.dialog = AsyncMock()
        mock_app.show_error_dialog = AsyncMock()

        # Mock failed config save
        mock_app.db_manager.update_setting.return_value = False

        # Import ConfigTab here to avoid import issues
        from mmm_savings_rate.gui import ConfigTab

        with patch.object(ConfigTab, '_load_config_values'):
            config_tab = ConfigTab(mock_app)

            # Mock form values
            with patch.object(config_tab, '_get_form_values') as mock_get_values:
                mock_get_values.return_value = {'pay': '/test/income.xlsx'}

                # Use asyncio.run to properly handle the async call
                # Avoid GLib event loop conflicts by using new thread
                result = None
                exception = None

                def run_async():
                    nonlocal result, exception
                    try:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        result = loop.run_until_complete(config_tab.save_config(None))
                        loop.close()
                    except Exception as e:
                        exception = e

                thread = threading.Thread(target=run_async)
                thread.start()
                thread.join()

                # Threading exceptions aren't always forwarded to the main thread
                # Make sure the test fails if it should
                if exception:
                    raise exception

                # Should show error dialog
                mock_app.show_error_dialog.assert_called_once()

                # Should NOT update file watcher or refresh plot
                mock_app.file_watcher.update_watched_files.assert_not_called()
                mock_app.plot_tab.refresh_plot.assert_not_called()


@unittest.skipIf(not GUI_AVAILABLE, "GUI dependencies not available")
class TestRealFileModification(unittest.TestCase):
    """Test file watching with actual file modifications."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_file = os.path.join(self.temp_dir, "test.xlsx")

        # Create test file
        with open(self.test_file, 'w') as f:
            f.write("initial content")

        # Create mock app
        self.mock_app = MagicMock()
        self.mock_app.plot_tab = MagicMock()

        # Create AsyncMock that returns a simple coroutine instead of another coroutine
        async def mock_refresh():
            return None

        self.mock_app.plot_tab.refresh_plot = AsyncMock(side_effect=mock_refresh)

        # Mock event loop
        self.mock_loop = MagicMock()
        self.mock_app._impl.loop = self.mock_loop
        self.mock_loop.is_running.return_value = True

        self.file_watcher = FileWatcher(self.mock_app)

    def tearDown(self):
        """Clean up test fixtures."""
        try:
            self.file_watcher.stop()
        except Exception:
            pass

        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    @patch('mmm_savings_rate.gui.asyncio.run_coroutine_threadsafe')
    def test_file_modification_triggers_refresh(self, mock_run_coroutine):
        """Test that modifying a watched file triggers plot refresh."""
        # Start watching the file
        self.file_watcher.watch_file(self.test_file)
        self.file_watcher.start()

        # Give observer time to start
        time.sleep(0.5)

        # Modify the file
        with open(self.test_file, 'w') as f:
            f.write("modified content")

        # Wait for file system event and debounce
        time.sleep(1.5)

        # Should have triggered refresh
        mock_run_coroutine.assert_called()


if __name__ == '__main__':
    unittest.main()
