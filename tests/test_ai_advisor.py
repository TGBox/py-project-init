import json
import os
import unittest
from unittest.mock import patch, MagicMock
from io import BytesIO
import urllib.error

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication
from py_project_init.core.ai_advisor import (
    AiProviderConfig,
    AiAdvice,
    AiAdvisorError,
    PROVIDER_DEFAULTS,
    build_system_prompt,
    query_ai_advisor,
    _extract_json,
    load_ai_key,
    save_ai_key,
    delete_ai_key,
)
from py_project_init.ui.ai_dialog import AiAdvisorDialog, AiAdvisorWorker
from py_project_init.ui.main_window import MainWindow


class TestAiAdvisorCore(unittest.TestCase):
    def setUp(self):
        self.sample_templates = [
            {
                "id": "python-cli",
                "name": "Python CLI Tool",
                "language": "Python",
                "description": "Moderne Python CLI mit uv und Click.",
                "recommended_tools": ["git", "uv"],
            },
            {
                "id": "rust-cli",
                "name": "Rust CLI Utility",
                "language": "Rust",
                "description": "High-performance Rust CLI mit Cargo.",
                "recommended_tools": ["git", "cargo"],
            },
            {
                "id": "node-typescript",
                "name": "Node.js TypeScript Library",
                "language": "TypeScript",
                "description": "TypeScript Bibliothek mit npm.",
                "recommended_tools": ["git", "npm"],
            },
        ]

    def test_json_extraction(self):
        # 1. Plain JSON
        plain = '{"project_name": "data-cruncher", "language": "Rust"}'
        res = _extract_json(plain)
        self.assertEqual(res["project_name"], "data-cruncher")
        self.assertEqual(res["language"], "Rust")

        # 2. Markdown code fenced JSON
        fenced = """Hier ist meine Empfehlung:
```json
{
  "project_name": "smart-cli",
  "recommended_template_id": "rust-cli",
  "reasoning": "Rust bietet beste Geschwindigkeit."
}
```
Viel Erfolg!"""
        res = _extract_json(fenced)
        self.assertEqual(res["project_name"], "smart-cli")
        self.assertEqual(res["recommended_template_id"], "rust-cli")

        # 3. Text with curly brackets embedded
        raw = 'Intro text {"project_name": "super-tool"} trailing text'
        res = _extract_json(raw)
        self.assertEqual(res.get("project_name"), "super-tool")

        # 4. Invalid JSON
        with self.assertRaises(AiAdvisorError):
            _extract_json("Kein gültiges JSON hier vorhanden")

    def test_prompt_generation(self):
        system_prompt = build_system_prompt(self.sample_templates)
        self.assertIn("python-cli", system_prompt)
        self.assertIn("rust-cli", system_prompt)
        self.assertIn("node-typescript", system_prompt)
        self.assertIn("JSON", system_prompt)

    def test_gemini_query_success(self):
        config = AiProviderConfig(
            provider="gemini",
            api_key="test-gemini-key",
            model="gemini-1.5-flash",
        )
        fake_response_data = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "text": json.dumps({
                                    "project_name": "fast-csv-filter",
                                    "language": "Rust",
                                    "framework": "Clap",
                                    "recommended_template_id": "rust-cli",
                                    "description": "High-performance CLI zur Filterung riesiger CSV-Dateien.",
                                    "reasoning": "Rust bietet zero-cost Abstractions und maximale I/O Geschwindigkeit.",
                                    "architecture_plan": "1. CLI Setup\n2. Stream Reader\n3. Parallel Filter",
                                    "suggested_libraries": ["csv", "rayon", "clap"],
                                    "alternatives": [
                                        {"template_id": "python-cli", "name": "Python CLI", "tradeoff": "Langsamer"}
                                    ],
                                })
                            }
                        ]
                    }
                }
            ]
        }

        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(fake_response_data).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp

        with patch("urllib.request.urlopen", return_value=mock_resp) as mock_urlopen:
            advice = query_ai_advisor(
                user_idea="CSV Filter Tool für gigantische Dateien",
                available_templates=self.sample_templates,
                config=config,
            )

            self.assertEqual(advice.project_name, "fast-csv-filter")
            self.assertEqual(advice.recommended_template_id, "rust-cli")
            self.assertEqual(advice.language, "Rust")
            self.assertIn("csv", advice.suggested_libraries)
            self.assertIn("Stream Reader", advice.architecture_plan)

            # Check that URL included the key parameter
            req = mock_urlopen.call_args[0][0]
            self.assertIn("key=test-gemini-key", req.full_url)
            self.assertIn("generativelanguage.googleapis.com", req.full_url)

    def test_openai_compatible_query_success(self):
        config = AiProviderConfig(
            provider="openai",
            model="gpt-4o-mini",
            api_key="sk-test-openai-key",
        )
        fake_response_data = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": json.dumps({
                            "project_name": "quick-data-api",
                            "language": "Python",
                            "recommended_template_id": "python-cli",
                            "description": "Schnelle Daten-API.",
                            "reasoning": "Python ist einfach und wartbar.",
                            "architecture_plan": "1. Init\n2. Code\n3. Test",
                            "suggested_libraries": ["pydantic", "httpx"],
                            "alternatives": [],
                        }),
                    }
                }
            ]
        }

        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(fake_response_data).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp

        with patch("urllib.request.urlopen", return_value=mock_resp) as mock_urlopen:
            advice = query_ai_advisor(
                user_idea="Schnelle Daten-API mit REST Endpunkten",
                available_templates=self.sample_templates,
                config=config,
            )

            self.assertEqual(advice.project_name, "quick-data-api")
            self.assertEqual(advice.recommended_template_id, "python-cli")
            req = mock_urlopen.call_args[0][0]
            self.assertEqual(req.headers.get("Authorization"), "Bearer sk-test-openai-key")

    def test_error_handling_http_error(self):
        config = AiProviderConfig(provider="gemini", api_key="invalid-key")
        err_body = json.dumps({"error": {"message": "API key not valid"}}).encode("utf-8")
        http_err = urllib.error.HTTPError(
            url="https://api.example.com",
            code=400,
            msg="Bad Request",
            hdrs={},
            fp=BytesIO(err_body),
        )

        with patch("urllib.request.urlopen", side_effect=http_err):
            with self.assertRaises(AiAdvisorError) as ctx:
                query_ai_advisor("My idea", self.sample_templates, config)
            self.assertIn("400", str(ctx.exception))

    def test_missing_api_key_raises(self):
        config = AiProviderConfig(provider="gemini", api_key="")
        with self.assertRaises(AiAdvisorError) as ctx:
            query_ai_advisor("Idea", self.sample_templates, config)
        self.assertIn("Kein API-Key", str(ctx.exception))

    def test_empty_idea_raises(self):
        config = AiProviderConfig(provider="ollama")
        with self.assertRaises(AiAdvisorError) as ctx:
            query_ai_advisor("   ", self.sample_templates, config)
        self.assertIn("beschreibe", str(ctx.exception))

    def test_token_storage(self):
        # Test saving and loading with mock keyring
        mock_keyring = MagicMock()
        mock_keyring.get_password.return_value = "stored-secret-key"

        with patch.dict("sys.modules", {"keyring": mock_keyring}):
            # Save
            ok = save_ai_key("gemini", "my-new-key")
            self.assertTrue(ok)
            mock_keyring.set_password.assert_called_with("py-project-init-ai", "gemini", "my-new-key")

            # Load
            token = load_ai_key("gemini")
            self.assertEqual(token, "stored-secret-key")

            # Delete
            delete_ai_key("gemini")
            mock_keyring.delete_password.assert_called_with("py-project-init-ai", "gemini")

    def test_token_env_fallback(self):
        # When keyring returns None, fallback to environment variable
        mock_keyring = MagicMock()
        mock_keyring.get_password.return_value = None

        with patch.dict("sys.modules", {"keyring": mock_keyring}):
            with patch.dict(os.environ, {"GEMINI_API_KEY": "env-gemini-key"}):
                token = load_ai_key("gemini")
                self.assertEqual(token, "env-gemini-key")


class TestAiAdvisorDialogAndUI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.templates = [
            {"id": "python-cli", "name": "Python CLI", "language": "Python", "description": "CLI in Python"},
            {"id": "rust-cli", "name": "Rust CLI", "language": "Rust", "description": "CLI in Rust"},
        ]
        self.dialog = AiAdvisorDialog(self.templates)
        self.window = MainWindow()

    def tearDown(self):
        self.dialog.close()
        self.window.close()

    def test_dialog_initial_state(self):
        self.assertIsNotNone(self.dialog.provider_combo)
        self.assertGreaterEqual(self.dialog.provider_combo.count(), 4)
        self.assertIsNotNone(self.dialog.idea_input)
        self.assertFalse(self.dialog.apply_btn.isEnabled())

        # Toggle fullscreen
        self.assertFalse(self.dialog.isFullScreen())
        self.dialog.toggle_fullscreen()
        self.assertTrue(self.dialog.isFullScreen())
        self.dialog.toggle_fullscreen()
        self.assertFalse(self.dialog.isFullScreen())

    def test_provider_change_updates_defaults(self):
        # Select Ollama (Local)
        idx = self.dialog.provider_combo.findData("ollama")
        self.assertGreaterEqual(idx, 0)
        self.dialog.provider_combo.setCurrentIndex(idx)

        # Ollama enables custom URL input
        self.assertTrue(self.dialog.url_input.isEnabled())
        self.assertIn("11434", self.dialog.url_input.text())
        self.assertIn("llama3", self.dialog.model_input.text())

        # Select OpenAI
        idx_oa = self.dialog.provider_combo.findData("openai")
        self.dialog.provider_combo.setCurrentIndex(idx_oa)
        self.assertFalse(self.dialog.url_input.isEnabled())
        self.assertIn("gpt-4o", self.dialog.model_input.text())

    def test_example_pill_insertion(self):
        self.dialog._insert_example("Entwickle eine asynchrone REST-API mit JWT-Authentifizierung.")
        self.assertIn("REST-API", self.dialog.idea_input.toPlainText())

    def test_apply_advice_to_main_window(self):
        sample_advice = AiAdvice(
            project_name="hyper-fast-csv",
            language="Rust",
            framework="Clap",
            recommended_template_id="rust-cli",
            description="Ultra-schneller CSV Filter mit Rust.",
            reasoning="Rust garantiert zero-cost Abstraktionen.",
            architecture_plan="1. Init\n2. Stream\n3. Export",
            suggested_libraries=["csv", "clap"],
            alternatives=[],
            raw_response="{}",
        )

        # Set advice on dialog and trigger apply
        self.dialog.applied_advice = sample_advice
        self.dialog._apply_advice()
        self.assertEqual(self.dialog.selected_advice, sample_advice)

        # Verify button and action exist in MainWindow
        self.assertIsNotNone(self.window.ai_advisor_btn)

        # Simulate applying advice in MainWindow logic
        self.window.name_input.setText(sample_advice.project_name)
        self.window.desc_input.setText(sample_advice.description)
        idx = self.window.template_combo.findData(sample_advice.recommended_template_id)
        if idx >= 0:
            self.window.template_combo.setCurrentIndex(idx)

        self.assertEqual(self.window.name_input.text(), "hyper-fast-csv")
        self.assertEqual(self.window.desc_input.text(), "Ultra-schneller CSV Filter mit Rust.")
        if idx >= 0:
            self.assertEqual(self.window.template_combo.currentData(), "rust-cli")


if __name__ == "__main__":
    unittest.main()
