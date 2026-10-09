import os
import unittest
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication
from py_project_init.ui.main_window import MainWindow


class TestMainWindow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.window = MainWindow()

    def tearDown(self):
        self.window.close()

    def test_window_components(self):
        """Verifies that all widgets and new options are properly loaded."""
        self.assertIsNotNone(self.window.template_combo)
        self.assertGreater(self.window.template_combo.count(), 0)

        # Check git hooks section
        self.assertTrue(self.window.git_hooks_enable_cb.isChecked())
        self.assertIn("pre-commit", self.window.hook_checkboxes)
        self.assertIn("post-commit", self.window.hook_checkboxes)

        # Check agent config section
        self.assertTrue(self.window.agent_configs_enable_cb.isChecked())
        self.assertIn("general_guidelines", self.window.agent_rule_checkboxes)
        self.assertIn("code-review", self.window.agent_skill_checkboxes)

        # Check script table interaction
        self.window.script_name_input.setText("my_task")
        self.window.script_cmd_input.setText("echo hello")
        self.window._add_custom_script()

        scripts = self.window._get_custom_scripts_dict()
        self.assertIn("my_task", scripts)
        self.assertEqual(scripts["my_task"], "echo hello")


if __name__ == "__main__":
    unittest.main()
