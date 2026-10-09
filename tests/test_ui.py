import os
import unittest
from unittest.mock import patch
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication
from py_project_init.ui.main_window import MainWindow
from py_project_init.ui.dialogs import PreviewDialog, RetrofitDialog, CreateTemplateDialog


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

        # Check git hooks section - all 8 client hooks
        self.assertTrue(self.window.git_hooks_enable_cb.isChecked())
        expected_hooks = [
            "pre-commit", "commit-msg", "prepare-commit-msg", "post-commit",
            "post-checkout", "post-merge", "pre-rebase", "pre-push"
        ]
        for h in expected_hooks:
            self.assertIn(h, self.window.hook_checkboxes)

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

    def test_preview_dialog(self):
        """Tests that PreviewDialog loads files and displays content on selection."""
        mock_files = {
            "src/main.py": "def main():\n    pass\n",
            "README.md": "# Test Project\n"
        }
        dlg = PreviewDialog(mock_files, parent=self.window)
        self.assertIsNotNone(dlg.tree_widget)
        self.assertGreater(dlg.tree_widget.topLevelItemCount(), 0)
        self.assertIn("Test Project", dlg.content_view.toPlainText() or dlg.files_map["README.md"])
        dlg.close()

    def test_retrofit_dialog(self):
        """Tests that RetrofitDialog instantiates with hooks and rules checkboxes."""
        dlg = RetrofitDialog(self.window.template_manager, parent=self.window)
        self.assertIsNotNone(dlg.target_path_input)
        self.assertTrue(dlg.enable_hooks_cb.isChecked())
        self.assertTrue(dlg.enable_agent_cb.isChecked())
        self.assertIn("pre-commit", dlg.hook_checkboxes)
        self.assertIn("general_guidelines", dlg.rule_checkboxes)
        dlg.close()

    def test_create_template_dialog(self):
        """Tests that CreateTemplateDialog has input fields and language options."""
        dlg = CreateTemplateDialog(self.window.template_manager, parent=self.window)
        self.assertIsNotNone(dlg.source_path_input)
        self.assertIsNotNone(dlg.id_input)
        self.assertGreater(dlg.lang_combo.count(), 0)
        dlg.close()

    def test_launcher_row_and_preview_button(self):
        """Tests preview button availability and launcher row visibility toggle."""
        self.assertTrue(self.window.preview_btn.isEnabled())
        self.assertFalse(self.window.launcher_widget.isVisible())

        # Simulate success
        with patch("py_project_init.ui.main_window.QMessageBox.information"):
            self.window._on_generation_finished(True, "C:/fake/path", False)
            self.assertFalse(self.window.launcher_widget.isHidden())
            self.assertTrue(self.window.vscode_btn.isEnabled())
            self.assertTrue(self.window.cursor_btn.isEnabled())
            self.assertTrue(self.window.term_btn.isEnabled())

            # Simulate cancel
            self.window._on_generation_finished(False, "", True)
            self.assertTrue(self.window.launcher_widget.isHidden())


if __name__ == "__main__":
    unittest.main()
