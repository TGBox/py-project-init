"""AI Project Advisor Dialog for choosing the best language, template, and architecture."""
from typing import Any
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QLineEdit, QComboBox, QGroupBox, QCheckBox,
    QProgressBar, QMessageBox, QScrollArea, QWidget, QApplication
)
from py_project_init.core.ai_advisor import (
    AiAdvice, AiProviderConfig, query_ai_advisor,
    load_ai_key, save_ai_key, delete_ai_key,
    PROVIDER_DEFAULTS, AiAdvisorError
)


class AiAdvisorWorker(QThread):
    """Executes the AI consultation in a background thread."""
    advice_ready = Signal(object)  # AiAdvice
    error_occurred = Signal(str)

    def __init__(
        self,
        user_idea: str,
        available_templates: list[dict[str, Any]],
        config: AiProviderConfig,
        parent=None,
    ):
        super().__init__(parent)
        self.user_idea = user_idea
        self.available_templates = available_templates
        self.config = config

    def run(self):
        try:
            advice = query_ai_advisor(
                self.user_idea,
                self.available_templates,
                self.config,
                timeout=45.0,
            )
            self.advice_ready.emit(advice)
        except Exception as e:
            self.error_occurred.emit(str(e))


class AiAdvisorDialog(QDialog):
    """Interactive dialog providing AI-driven suggestions for templates, titles, and architecture."""

    def __init__(self, available_templates: list[dict[str, Any]], parent=None):
        super().__init__(parent)
        self.setWindowTitle("✨ KI-Projektberater & Entscheidungshilfe")
        self.resize(880, 720)
        self.setMinimumSize(680, 520)
        self.setWindowFlags(self.windowFlags() | Qt.WindowMaximizeButtonHint)

        self.available_templates = available_templates
        self.worker: AiAdvisorWorker | None = None
        self.applied_advice: AiAdvice | None = None

        # F11 Fullscreen support (adheres to GUI rules)
        self.fullscreen_shortcut = QShortcut(QKeySequence(Qt.Key_F11), self)
        self.fullscreen_shortcut.activated.connect(self._toggle_fullscreen)

        self._init_ui()
        self._on_provider_changed()

    def toggle_fullscreen(self):
        """Toggles fullscreen and windowed mode (F11)."""
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    _toggle_fullscreen = toggle_fullscreen

    @property
    def selected_advice(self) -> AiAdvice | None:
        """Returns the currently selected / applied advice."""
        return self.applied_advice

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_F11:
            self._toggle_fullscreen()
            event.accept()
        else:
            super().keyPressEvent(event)

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(14, 14, 14, 14)
        main_layout.setSpacing(12)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(12)
        scroll.setWidget(container)
        main_layout.addWidget(scroll, 1)

        # Header Banner
        header = QLabel(
            "<b>Unentschlossen bei Sprache, Architektur oder Projektname?</b><br>"
            "<span style='color: #a9b1d6;'>Beschreibe deine Idee oder Anforderungen. Die KI analysiert "
            "alle verfügbaren Vorlagen und empfiehlt dir das beste Setup inklusive Umsetzungsplan.</span>"
        )
        header.setWordWrap(True)
        header.setStyleSheet("background: #24283b; padding: 10px; border-radius: 6px; border: 1px solid #414868;")
        layout.addWidget(header)

        # ── Provider & Model Config Box ──
        config_box = QGroupBox("⚙️ KI-Provider & Modell-Einstellungen")
        config_layout = QVBoxLayout(config_box)
        config_layout.setSpacing(8)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Provider:"))
        self.provider_combo = QComboBox()
        self.provider_combo.addItem("Google Gemini", "gemini")
        self.provider_combo.addItem("OpenAI (ChatGPT)", "openai")
        self.provider_combo.addItem("OpenRouter", "openrouter")
        self.provider_combo.addItem("Ollama (Lokal / Kostenlos)", "ollama")
        self.provider_combo.addItem("Benutzerdefiniert (OpenAI-kompatibel)", "custom")
        self.provider_combo.currentIndexChanged.connect(self._on_provider_changed)
        row1.addWidget(self.provider_combo, 1)

        row1.addWidget(QLabel("Modell:"))
        self.model_input = QLineEdit()
        self.model_input.setPlaceholderText("z. B. gemini-1.5-flash")
        row1.addWidget(self.model_input, 1)
        config_layout.addLayout(row1)

        # Row 2: API Key & URL
        self.key_row = QHBoxLayout()
        self.key_label = QLabel("API-Key:")
        self.key_input = QLineEdit()
        self.key_input.setEchoMode(QLineEdit.Password)
        self.key_input.setPlaceholderText("API-Key eintragen...")
        self.key_row.addWidget(self.key_label)
        self.key_row.addWidget(self.key_input, 1)

        self.save_key_cb = QCheckBox("Im Windows-Tresor merken")
        self.save_key_cb.setChecked(True)
        self.key_row.addWidget(self.save_key_cb)
        config_layout.addLayout(self.key_row)

        self.url_row = QHBoxLayout()
        self.url_label = QLabel("Basis-URL:")
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Standard-URL des Providers")
        self.url_row.addWidget(self.url_label)
        self.url_row.addWidget(self.url_input, 1)
        config_layout.addLayout(self.url_row)

        layout.addWidget(config_box)

        # ── User Idea Input Box ──
        idea_box = QGroupBox("💡 Deine Projektidee / Anforderungen")
        idea_layout = QVBoxLayout(idea_box)
        idea_layout.setSpacing(6)

        self.idea_input = QTextEdit()
        self.idea_input.setMinimumHeight(110)
        self.idea_input.setPlaceholderText(
            "Beschreibe hier dein Vorhaben. Zum Beispiel:\n"
            "• 'Ich möchte ein Tool bauen, das PDF-Rechnungen per OCR einliest, Metadaten extrahiert und in einer SQLite-DB speichert.'\n"
            "• 'Ein schnelles Terminal-Dashboard zur Überwachung von Server-Metriken mit schönen Charts.'\n"
            "• 'Ein Web-Portal mit FastAPI Backend und modernem React Frontend für Kundenverwaltung.'"
        )
        idea_layout.addWidget(self.idea_input)

        btn_row = QHBoxLayout()
        self.example_btn = QPushButton("Beispielidee einfügen")
        self.example_btn.setObjectName("toolButton")
        self.example_btn.clicked.connect(self._insert_example)
        btn_row.addWidget(self.example_btn)
        btn_row.addStretch()

        self.query_btn = QPushButton("✨ Empfehlung anfordern")
        self.query_btn.setStyleSheet("font-weight: bold; background-color: #7aa2f7; color: #1a1b26; padding: 6px 14px;")
        self.query_btn.clicked.connect(self._start_consultation)
        btn_row.addWidget(self.query_btn)
        idea_layout.addLayout(btn_row)

        layout.addWidget(idea_box)

        # ── Loading Indicator ──
        self.progress_container = QWidget()
        prog_layout = QVBoxLayout(self.progress_container)
        self.status_label = QLabel("KI analysiert deine Idee und gleicht Templates ab...")
        self.status_label.setStyleSheet("color: #7aa2f7; font-weight: 600;")
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # indeterminate pulse
        prog_layout.addWidget(self.status_label)
        prog_layout.addWidget(self.progress_bar)
        self.progress_container.setVisible(False)
        layout.addWidget(self.progress_container)

        # ── Result Presentation Box ──
        self.result_box = QGroupBox("🎯 KI-Empfehlung & Architektur-Vorschlag")
        self.result_layout = QVBoxLayout(self.result_box)
        self.result_layout.setSpacing(10)

        # Highlight Card
        self.highlight_card = QWidget()
        self.highlight_card.setStyleSheet(
            "background: #24283b; border: 1px solid #7aa2f7; border-radius: 6px; padding: 10px;"
        )
        hl_layout = QVBoxLayout(self.highlight_card)
        hl_layout.setSpacing(4)

        self.res_template_label = QLabel("<b>Empfohlene Vorlage:</b> -")
        self.res_template_label.setStyleSheet("font-size: 14px; color: #7aa2f7;")
        self.res_name_label = QLabel("<b>Vorgeschlagener Projektname:</b> -")
        self.res_desc_label = QLabel("<b>Beschreibung:</b> -")
        self.res_desc_label.setWordWrap(True)

        hl_layout.addWidget(self.res_template_label)
        hl_layout.addWidget(self.res_name_label)
        hl_layout.addWidget(self.res_desc_label)
        self.result_layout.addWidget(self.highlight_card)

        # Details text (Reasoning & Architecture Plan)
        self.details_view = QTextEdit()
        self.details_view.setReadOnly(True)
        self.details_view.setMinimumHeight(200)
        self.result_layout.addWidget(self.details_view)

        # Libraries & Alternatives info
        self.extra_info_label = QLabel()
        self.extra_info_label.setWordWrap(True)
        self.extra_info_label.setStyleSheet("color: #9ece6a;")
        self.result_layout.addWidget(self.extra_info_label)

        self.result_box.setVisible(False)
        layout.addWidget(self.result_box)

        # ── Bottom Action Bar ──
        footer = QHBoxLayout()
        self.copy_btn = QPushButton("📋 Empfehlung kopieren")
        self.copy_btn.setEnabled(False)
        self.copy_btn.clicked.connect(self._copy_to_clipboard)
        footer.addWidget(self.copy_btn)

        footer.addStretch()

        self.cancel_btn = QPushButton("Schließen")
        self.cancel_btn.clicked.connect(self.reject)
        footer.addWidget(self.cancel_btn)

        self.apply_btn = QPushButton("✔ In Projekt übernehmen")
        self.apply_btn.setEnabled(False)
        self.apply_btn.setStyleSheet(
            "font-weight: bold; background-color: #9ece6a; color: #1a1b26; padding: 6px 16px;"
        )
        self.apply_btn.clicked.connect(self._apply_advice)
        footer.addWidget(self.apply_btn)

        main_layout.addLayout(footer)

    def _on_provider_changed(self):
        provider = self.provider_combo.currentData()
        info = PROVIDER_DEFAULTS.get(provider, {})

        # Default model
        self.model_input.setText(info.get("default_model", ""))
        self.url_input.setText(info.get("base_url", ""))

        needs_key = info.get("needs_key", True)
        self.key_label.setVisible(needs_key)
        self.key_input.setVisible(needs_key)
        self.save_key_cb.setVisible(needs_key)

        if needs_key:
            stored_key = load_ai_key(provider)
            self.key_input.setText(stored_key)
        else:
            self.key_input.clear()

        # Custom URL row is only editable for custom or ollama
        is_custom_or_local = provider in ("custom", "ollama")
        self.url_input.setEnabled(is_custom_or_local)

    def _insert_example(self, example_text: str | None = None):
        if example_text:
            self.idea_input.setText(example_text)
            return

        examples = [
            "Ich möchte ein schnelles Command-Line Tool zur Überprüfung von SSL-Zertifikaten und Ablaufdaten bauen, das JSON ausgeben kann.",
            "Ein interaktives Terminal-Dashboard mit Tastaturkürzeln zur Analyse von lokalen Logdateien.",
            "Ein modernes Webportal für Inventarverwaltung mit REST API im Backend und schnellem React-Frontend.",
            "Ein 2D Retro-Arcade Spiel mit Soundeffekten, Sprite-Animationen und Highscore-Tabelle.",
            "Ein Cross-Platform Desktop-Programm mit sauberer GUI zur Verwaltung von Aufgaben und Notizen.",
        ]
        import random
        self.idea_input.setText(random.choice(examples))

    def _start_consultation(self):
        idea = self.idea_input.toPlainText().strip()
        if not idea:
            QMessageBox.warning(self, "Eingabe fehlt", "Bitte beschreibe zuerst deine Idee oder deine Anforderungen.")
            return

        provider = self.provider_combo.currentData()
        info = PROVIDER_DEFAULTS.get(provider, {})
        api_key = self.key_input.text().strip()

        if info.get("needs_key") and not api_key:
            QMessageBox.warning(
                self,
                "API-Key erforderlich",
                f"Für den Provider '{info.get('name', provider)}' ist ein API-Key notwendig.\n"
                f"Bitte trage deinen Key ein oder nutze 'Ollama' für eine lokale Ausführung.",
            )
            return

        # Save key if requested
        if info.get("needs_key") and self.save_key_cb.isChecked() and api_key:
            save_ai_key(provider, api_key)

        config = AiProviderConfig(
            provider=provider,
            api_key=api_key,
            model=self.model_input.text().strip() or info.get("default_model", ""),
            base_url=self.url_input.text().strip() or info.get("base_url", ""),
        )

        self.query_btn.setEnabled(False)
        self.progress_container.setVisible(True)
        self.result_box.setVisible(False)
        self.apply_btn.setEnabled(False)
        self.copy_btn.setEnabled(False)

        self.worker = AiAdvisorWorker(idea, self.available_templates, config, self)
        self.worker.advice_ready.connect(self._on_advice_ready)
        self.worker.error_occurred.connect(self._on_error)
        self.worker.start()

    def _on_advice_ready(self, advice: AiAdvice):
        self.progress_container.setVisible(False)
        self.query_btn.setEnabled(True)
        self.applied_advice = advice

        # Find template name
        tpl_name = advice.recommended_template_id
        for t in self.available_templates:
            if t.get("id") == advice.recommended_template_id:
                tpl_name = f"{t.get('name', tpl_name)} ({advice.recommended_template_id})"
                break

        self.res_template_label.setText(f"<b>Empfohlene Vorlage:</b> <span style='color: #7aa2f7;'>{tpl_name}</span>")
        self.res_name_label.setText(f"<b>Vorgeschlagener Projektname:</b> <code>{advice.project_name}</code>")
        self.res_desc_label.setText(f"<b>Beschreibung:</b> {advice.description}")

        # Details
        html_details = f"<h3>💡 Warum {advice.language or 'dieses Setup'}?</h3>"
        html_details += f"<p>{advice.reasoning.replace(chr(10), '<br>')}</p>"
        html_details += "<h3>🏗️ Empfohlener Architektur- und Implementierungsweg</h3>"
        html_details += f"<p>{advice.architecture_plan.replace(chr(10), '<br>')}</p>"
        self.details_view.setHtml(html_details)

        # Extra info
        extra = []
        if advice.suggested_libraries:
            extra.append(f"<b>Empfohlene Bibliotheken:</b> {', '.join(advice.suggested_libraries)}")
        if advice.alternatives:
            alt_texts = [f"{alt.get('name', alt.get('template_id', ''))}: {alt.get('tradeoff', '')}" for alt in advice.alternatives]
            extra.append(f"<b>Mögliche Alternativen:</b><br>• " + "<br>• ".join(alt_texts))

        self.extra_info_label.setText("<br>".join(extra))

        self.result_box.setVisible(True)
        self.apply_btn.setEnabled(True)
        self.copy_btn.setEnabled(True)

    def _on_error(self, error_msg: str):
        self.progress_container.setVisible(False)
        self.query_btn.setEnabled(True)
        QMessageBox.critical(
            self,
            "Fehler bei der KI-Anfrage",
            f"Die Anfrage an den KI-Dienst konnte nicht abgeschlossen werden:\n\n{error_msg}",
        )

    def _copy_to_clipboard(self):
        if not self.applied_advice:
            return
        adv = self.applied_advice
        text = (
            f"Projekt-Empfehlung: {adv.project_name}\n"
            f"Vorlage: {adv.recommended_template_id} ({adv.language} / {adv.framework})\n"
            f"Beschreibung: {adv.description}\n\n"
            f"Begründung:\n{adv.reasoning}\n\n"
            f"Architektur- & Umsetzungsplan:\n{adv.architecture_plan}\n"
        )
        if adv.suggested_libraries:
            text += f"\nBibliotheken: {', '.join(adv.suggested_libraries)}\n"
        QApplication.clipboard().setText(text)
        QMessageBox.information(self, "Kopiert", "Die Empfehlung wurde in die Zwischenablage kopiert.")

    def _apply_advice(self):
        self.accept()
