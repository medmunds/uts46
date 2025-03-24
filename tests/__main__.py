import sys
import unittest

if __name__ == "__main__":
    test_suite = unittest.defaultTestLoader.discover(".", pattern="test_*.py")
    runner = unittest.TextTestRunner()
    result = runner.run(test_suite)
    sys.exit(not result.wasSuccessful())
