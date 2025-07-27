#!/usr/bin/env python3
"""
Main test module for briefcase dev --test command.

Briefcase expects a test module with this specific name pattern.
This module discovers and runs all tests in the tests directory.
"""
import sys
import unittest


def main():
    """Main test entry point for briefcase."""
    # Discover and run all tests
    loader = unittest.TestLoader()
    start_dir = 'tests'
    suite = loader.discover(start_dir, pattern='test*.py')

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Print explicit result for briefcase
    if result.wasSuccessful():
        print("\n=== All tests passed! ===")
        # Exit with success code so briefcase detects success
        sys.exit(0)
    else:
        print(
            f"\n=== Tests failed: {len(result.failures)} failures, {len(result.errors)} errors ==="
        )
        # Exit with failure code so briefcase detects failure
        sys.exit(1)


if __name__ == '__main__':
    main()
