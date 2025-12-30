import unittest
import sys
import os

# Add root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestImports(unittest.TestCase):
    def test_imports(self):
        """Test that all modules can be imported without error."""
        try:
            from core import app, database, event_bus
            from plugins import netease, qqmusic, bilibili
            from notifiers import wecom
            from domain import models
            print("Imports successful")
        except ImportError as e:
            self.fail(f"Import failed: {e}")

if __name__ == '__main__':
    unittest.main()
