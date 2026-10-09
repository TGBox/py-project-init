import json
import re
import sys
import shutil
from pathlib import Path
from PySide6.QtCore import QThread, Signal, QSettings, QByteArray, QUrl, Qt
from PySide6.QtGui import QAction, QKeySequence, QDesktopServices
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QComboBox, QCheckBox, QPushButton, QTextEdit,
    QFileDialog, QLabel, QGroupBox, QMessageBox, QScrollArea,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView
)
from py_project_init.core.generator import TemplateManager
from py_project_init.ui.styles import DARK_THEME

CHECKED_TOOLS = ["git", "uv", "cargo", "npm"]
_VALID_NAME = re.compile(r"^[a-zA-Z][a-zA-Z0-9_-]*$")


class GenerateWorker(QThread):
    log_signal = Signal(str)
    # ok, target_dir_str, was_cancelled
    finished_signal = Signal(bool, str, bool)

    def __init__(self, generator: TemplateManager, target_dir: Path, template_id: str, context: dict):
        super().__init__()
        self.generator = generator
        self.target_dir = target_dir
        self.template_id = template_id
        self.context = context
        self._cancelled = False

    def cancel(self):
        """Requests cancellation of running generation."""
        self._cancelled = True
        self.requestInterruption()

    def run(self):
        try:
            self.generator.generate(
                self.target_dir,
                self.template_id,
                self.context,
                log_callback=self.log_signal.emit,
                is_cancelled=lambda: self._cancelled or self.isInterruptionRequested()
            )
            self.finished_signal.emit(True, str(self.target_dir), False)
        except InterruptedError:
            self.log_signal.emit("\n⚠ Vorgang wurde durch den Benutzer abgebrochen.")
            self.finished_signal.emit(False, "", True)
        except Exception as e:
            self.log_signal.emit(f"\nFehler: {str(e)}")
            self.finished_signal.emit(False, "", False)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Project Scaffolder - Projekt-Initialisierung")
        self.resize(840, 880)

        # Persistent settings
        self.settings = QSettings("DaniBani", "PyProjectInit")

        # Template initialization
        base_dir = Path(__file__).resolve().parent.parent.parent.parent
        self.default_templates_dir = base_dir / "templates"

        # Load any custom templates directories from settings
        custom_dirs = [Path(p) for p in self.settings.value("custom_templates_dirs", []) if Path(p).is_dir()]
        self.template_manager = TemplateManager(self.default_templates_dir, custom_dirs=custom_dirs)
        self.generator = self.template_manager

        self.tool_statuses: dict[str, bool] = {}
        self.option_checkboxes: dict[str, QCheckBox] = {}
        self.option_selects: dict[str, QComboBox] = {}
        self.hook_checkboxes: dict[str, QCheckBox] = {}
        self.agent_rule_checkboxes: dict[str, QCheckBox] = {}
        self.agent_skill_checkboxes: dict[str, QCheckBox] = {}
        self._last_target_dir: str = ""
        self.worker: GenerateWorker | None = None

        self._init_menu()
        self._init_ui()
        self._apply_theme()
        self._load_saved_settings()
        self._refresh_tool_status()
        self._populate_templates()
        self._populate_git_hooks()
        self._refresh_agent_configs()

    def _apply_theme(self):
        """Applies the modern dark stylesheet to the main window."""
        self.setStyleSheet(DARK_THEME)

    # ── Menüleiste & Aktionen ───────────────────────────────────────────────

    def _init_menu(self):
        menubar = self.menuBar()

        # Datei Menü
        file_menu = menubar.addMenu("Datei")

        open_target_action = QAction("Zielordner wählen...", self)
        open_target_action.setShortcut(QKeySequence("Ctrl+O"))
        open_target_action.triggered.connect(self._select_path)
        file_menu.addAction(open_target_action)

        file_menu.addSeparator()

        exit_action = QAction("Beenden", self)
        exit_action.setShortcut(QKeySequence("Ctrl+Q"))
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Vorlagen Menü
        template_menu = menubar.addMenu("Vorlagen")

        reload_action = QAction("Vorlagen neu laden", self)
        reload_action.setShortcut(QKeySequence("Ctrl+R"))
        reload_action.triggered.connect(self._reload_templates)
        template_menu.addAction(reload_action)

        open_tpl_folder_action = QAction("Standard-Vorlagenordner im Explorer öffnen", self)
        open_tpl_folder_action.triggered.connect(self._open_templates_dir)
        template_menu.addAction(open_tpl_folder_action)

        open_hooks_folder_action = QAction("Git-Hooks-Ordner im Explorer öffnen", self)
        open_hooks_folder_action.triggered.connect(self._open_hooks_dir)
        template_menu.addAction(open_hooks_folder_action)

        open_agents_folder_action = QAction("Agenten-Asset-Ordner im Explorer öffnen", self)
        open_agents_folder_action.triggered.connect(self._open_agents_dir)
        template_menu.addAction(open_agents_folder_action)

        add_custom_tpl_action = QAction("Benutzerdefinierten Vorlagen-Ordner hinzufügen...", self)
        add_custom_tpl_action.triggered.connect(self._add_custom_templates_dir)
        template_menu.addAction(add_custom_tpl_action)

        reset_custom_tpl_action = QAction("Zusätzliche Vorlagen-Ordner zurücksetzen", self)
        reset_custom_tpl_action.triggered.connect(self._reset_custom_templates_dirs)
        template_menu.addAction(reset_custom_tpl_action)

        # Ansicht Menü (Fullscreen & Windowed mode per user rule)
        view_menu = menubar.addMenu("Ansicht")

        self.fullscreen_action = QAction("Vollbildmodus", self)
        self.fullscreen_action.setCheckable(True)
        self.fullscreen_action.setShortcut(QKeySequence("F11"))
        self.fullscreen_action.triggered.connect(self.toggle_fullscreen)
        view_menu.addAction(self.fullscreen_action)

        clear_log_action = QAction("Log leeren", self)
        clear_log_action.setShortcut(QKeySequence("Ctrl+L"))
        clear_log_action.triggered.connect(lambda: self.log_view.clear())
        view_menu.addAction(clear_log_action)

        # Hilfe Menü
        help_menu = menubar.addMenu("Hilfe")
        about_action = QAction("Über PyProjectInit...", self)
        about_action.triggered.connect(self._show_about_dialog)
        help_menu.addAction(about_action)

    def toggle_fullscreen(self):
        """Toggles between fullscreen and normal windowed mode."""
        if self.isFullScreen():
            self.showNormal()
            self.fullscreen_action.setChecked(False)
            self.statusBar().showMessage("Fenstermodus aktiviert", 2500)
        else:
            self.showFullScreen()
            self.fullscreen_action.setChecked(True)
            self.statusBar().showMessage("Vollbildmodus aktiviert (Drücke F11 zum Beenden)", 3000)

    # ── UI Aufbau ───────────────────────────────────────────────────────────

    def _init_ui(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        self.setCentralWidget(scroll)

        container = QWidget()
        scroll.setWidget(container)

        layout = QVBoxLayout(container)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        # 1. CLI Tools Statusleiste
        tools_group = QGroupBox("CLI-Tool Status (im System-PATH)")
        self.tools_layout = QHBoxLayout(tools_group)
        refresh_tools_btn = QPushButton("Neu prüfen")
        refresh_tools_btn.setObjectName("toolButton")
        refresh_tools_btn.clicked.connect(self._refresh_tool_status)
        self.tools_layout.addWidget(refresh_tools_btn)
        self.tools_layout.addStretch()
        layout.addWidget(tools_group)

        # 2. Basis-Metadaten
        meta_group = QGroupBox("Projekt-Stammdaten")
        meta_layout = QVBoxLayout(meta_group)

        lbl_name = QLabel("Projektname:")
        lbl_name.setObjectName("formLabel")
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("z. B. my-super-service (Buchstaben, Ziffern, - und _)")
        self.name_input.textChanged.connect(self._validate_name)
        self.name_error_label = QLabel()
        self.name_error_label.setStyleSheet("color: #f7768e; font-size: 11px; margin-top: 2px;")
        self.name_error_label.setVisible(False)

        lbl_desc = QLabel("Beschreibung:")
        lbl_desc.setObjectName("formLabel")
        self.desc_input = QLineEdit()
        self.desc_input.setPlaceholderText("Kurze Beschreibung des Projekts")

        lbl_path = QLabel("Speicherort (Basisordner):")
        lbl_path.setObjectName("formLabel")
        path_layout = QHBoxLayout()
        self.path_input = QLineEdit()
        self.path_input.setPlaceholderText("Verzeichnis, in dem der neue Projektordner angelegt wird...")
        self.path_input.textChanged.connect(self._save_path_setting)
        browse_btn = QPushButton("Zielordner wählen...")
        browse_btn.clicked.connect(self._select_path)
        path_layout.addWidget(self.path_input)
        path_layout.addWidget(browse_btn)

        meta_layout.addWidget(lbl_name)
        meta_layout.addWidget(self.name_input)
        meta_layout.addWidget(self.name_error_label)
        meta_layout.addWidget(lbl_desc)
        meta_layout.addWidget(self.desc_input)
        meta_layout.addWidget(lbl_path)
        meta_layout.addLayout(path_layout)
        layout.addWidget(meta_group)

        # 3. Template & Template-Optionen
        tpl_group = QGroupBox("Projekt-Vorlage & Vorlagenoptionen")
        tpl_layout = QVBoxLayout(tpl_group)

        tpl_header_layout = QHBoxLayout()
        lbl_tpl = QLabel("Vorlage auswählen:")
        lbl_tpl.setObjectName("formLabel")
        tpl_header_layout.addWidget(lbl_tpl)
        tpl_header_layout.addStretch()

        reload_tpl_btn = QPushButton("🔄 Neu laden")
        reload_tpl_btn.setObjectName("toolButton")
        reload_tpl_btn.clicked.connect(self._reload_templates)
        tpl_header_layout.addWidget(reload_tpl_btn)

        open_tpl_btn = QPushButton("📁 Vorlagen-Ordner")
        open_tpl_btn.setObjectName("toolButton")
        open_tpl_btn.clicked.connect(self._open_templates_dir)
        tpl_header_layout.addWidget(open_tpl_btn)

        self.template_combo = QComboBox()
        self.template_combo.currentIndexChanged.connect(self._on_template_changed)
        self.template_desc_label = QLabel()
        self.template_desc_label.setObjectName("mutedLabel")
        self.template_desc_label.setWordWrap(True)

        self.options_box = QGroupBox("Vorlagenspezifische Zusatzoptionen")
        self.options_layout = QVBoxLayout(self.options_box)

        tpl_layout.addLayout(tpl_header_layout)
        tpl_layout.addWidget(self.template_combo)
        tpl_layout.addWidget(self.template_desc_label)
        tpl_layout.addWidget(self.options_box)
        layout.addWidget(tpl_group)

        # 4. Git-Hooks Sektion
        self.git_hooks_box = QGroupBox("Git-Hooks Integration")
        hooks_box_layout = QVBoxLayout(self.git_hooks_box)

        self.git_hooks_enable_cb = QCheckBox("Git-Hooks in das Projekt einrichten (.git/hooks/)")
        self.git_hooks_enable_cb.setChecked(True)
        self.git_hooks_enable_cb.setStyleSheet("font-weight: 600; color: #7aa2f7;")
        hooks_box_layout.addWidget(self.git_hooks_enable_cb)

        self.git_hooks_container = QWidget()
        self.git_hooks_list_layout = QVBoxLayout(self.git_hooks_container)
        self.git_hooks_list_layout.setContentsMargins(16, 4, 4, 4)
        self.git_hooks_list_layout.setSpacing(6)
        hooks_box_layout.addWidget(self.git_hooks_container)
        self.git_hooks_enable_cb.toggled.connect(self.git_hooks_container.setEnabled)
        layout.addWidget(self.git_hooks_box)

        # 5. Erweiterte Konfiguration & Metadaten (Autor, Lizenz, Custom Scripts)
        self.advanced_box = QGroupBox("Projekt-Metadaten & Benutzerdefinierte Skripte")
        adv_layout = QVBoxLayout(self.advanced_box)

        author_row = QHBoxLayout()
        vbox_author = QVBoxLayout()
        vbox_author.addWidget(QLabel("Autor:"))
        self.author_input = QLineEdit()
        self.author_input.setPlaceholderText("z. B. Max Mustermann")
        self.author_input.textChanged.connect(lambda t: self.settings.setValue("author_name", t.strip()))
        vbox_author.addWidget(self.author_input)

        vbox_email = QVBoxLayout()
        vbox_email.addWidget(QLabel("E-Mail:"))
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("z. B. max@example.com")
        self.email_input.textChanged.connect(lambda t: self.settings.setValue("author_email", t.strip()))
        vbox_email.addWidget(self.email_input)

        vbox_license = QVBoxLayout()
        vbox_license.addWidget(QLabel("Lizenz:"))
        self.license_combo = QComboBox()
        self.license_combo.addItems(["MIT", "Apache-2.0", "GPL-3.0", "BSD-3-Clause", "Proprietary", "Keine"])
        self.license_combo.currentTextChanged.connect(lambda t: self.settings.setValue("license", t))
        vbox_license.addWidget(self.license_combo)

        author_row.addLayout(vbox_author)
        author_row.addLayout(vbox_email)
        author_row.addLayout(vbox_license)
        adv_layout.addLayout(author_row)

        lbl_scripts = QLabel("Zusätzliche Projekt-Skripte (z. B. in pyproject.toml oder package.json):")
        lbl_scripts.setObjectName("formLabel")
        adv_layout.addWidget(lbl_scripts)

        script_input_row = QHBoxLayout()
        self.script_name_input = QLineEdit()
        self.script_name_input.setPlaceholderText("Skript-Name (z.B. format)")
        self.script_cmd_input = QLineEdit()
        self.script_cmd_input.setPlaceholderText("Befehl (z.B. ruff format .)")
        add_script_btn = QPushButton("➕ Hinzufügen")
        add_script_btn.setObjectName("toolButton")
        add_script_btn.clicked.connect(self._add_custom_script)
        remove_script_btn = QPushButton("➖ Entfernen")
        remove_script_btn.setObjectName("toolButton")
        remove_script_btn.clicked.connect(self._remove_custom_script)

        script_input_row.addWidget(self.script_name_input, 1)
        script_input_row.addWidget(self.script_cmd_input, 2)
        script_input_row.addWidget(add_script_btn)
        script_input_row.addWidget(remove_script_btn)
        adv_layout.addLayout(script_input_row)

        self.scripts_table = QTableWidget(0, 2)
        self.scripts_table.setHorizontalHeaderLabels(["Name", "Befehl"])
        self.scripts_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.scripts_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.scripts_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.scripts_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.scripts_table.setMaximumHeight(120)
        adv_layout.addWidget(self.scripts_table)
        layout.addWidget(self.advanced_box)

        # 6. Agenten-Regeln & Skills Sektion
        self.agent_box = QGroupBox("Agenten-Regeln & Skills (.agents/ & AGENTS.md)")
        agent_box_layout = QVBoxLayout(self.agent_box)

        self.agent_configs_enable_cb = QCheckBox("Agenten-Konfiguration für Coding-Assistenten generieren")
        self.agent_configs_enable_cb.setChecked(True)
        self.agent_configs_enable_cb.setStyleSheet("font-weight: 600; color: #7aa2f7;")
        agent_box_layout.addWidget(self.agent_configs_enable_cb)

        self.agent_container = QWidget()
        self.agent_container_layout = QVBoxLayout(self.agent_container)
        self.agent_container_layout.setContentsMargins(16, 4, 4, 4)

        lbl_rules = QLabel("Vorgeschlagene Regeln (.agents/rules/):")
        lbl_rules.setStyleSheet("font-weight: 600; color: #bb9af7;")
        self.agent_container_layout.addWidget(lbl_rules)
        self.agent_rules_layout = QVBoxLayout()
        self.agent_container_layout.addLayout(self.agent_rules_layout)

        lbl_skills = QLabel("Vorgeschlagene Skills (.agents/skills/):")
        lbl_skills.setStyleSheet("font-weight: 600; color: #bb9af7; margin-top: 6px;")
        self.agent_container_layout.addWidget(lbl_skills)
        self.agent_skills_layout = QVBoxLayout()
        self.agent_container_layout.addLayout(self.agent_skills_layout)

        agent_box_layout.addWidget(self.agent_container)
        self.agent_configs_enable_cb.toggled.connect(self.agent_container.setEnabled)
        layout.addWidget(self.agent_box)

        # 7. Buttons & Log
        btn_row = QHBoxLayout()
        self.run_btn = QPushButton("▶  Projekt initialisieren")
        self.run_btn.setObjectName("primaryButton")
        self.run_btn.clicked.connect(self._start_generation)

        self.cancel_btn = QPushButton("✖  Abbrechen")
        self.cancel_btn.setObjectName("cancelButton")
        self.cancel_btn.clicked.connect(self._cancel_generation)
        self.cancel_btn.setVisible(False)

        self.open_btn = QPushButton("📂  Im Explorer öffnen")
        self.open_btn.setObjectName("successButton")
        self.open_btn.clicked.connect(self._open_in_explorer)
        self.open_btn.setVisible(False)

        btn_row.addWidget(self.run_btn)
        btn_row.addWidget(self.cancel_btn)
        btn_row.addWidget(self.open_btn)

        lbl_log = QLabel("Status / Ausführungsprotokoll:")
        lbl_log.setObjectName("formLabel")
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMinimumHeight(160)

        layout.addLayout(btn_row)
        layout.addWidget(lbl_log)
        layout.addWidget(self.log_view)

        # Statusleiste
        self.statusBar().showMessage("Bereit")

    # ── Eingabevalidierung ──────────────────────────────────────────────────

    def _validate_name(self, text: str) -> bool:
        """Validates the project name against naming constraints."""
        text = text.strip()
        if not text:
            self.name_error_label.setVisible(False)
            return False
        if not _VALID_NAME.match(text):
            self.name_error_label.setText(
                "⚠ Nur Buchstaben, Ziffern, Bindestrich und Unterstrich erlaubt. "
                "Muss mit einem Buchstaben beginnen."
            )
            self.name_error_label.setVisible(True)
            return False
        self.name_error_label.setVisible(False)
        return True

    # ── CLI Tool Status ─────────────────────────────────────────────────────

    def _refresh_tool_status(self):
        for i in reversed(range(1, self.tools_layout.count() - 1)):
            widget = self.tools_layout.takeAt(i).widget()
            if widget:
                widget.deleteLater()

        for tool in CHECKED_TOOLS:
            available = bool(shutil.which(tool))
            self.tool_statuses[tool] = available
            badge = QLabel(f" {'✔' if available else '✖'} {tool} ")
            bg_color = "#27ae60" if available else "#c0392b"
            badge.setStyleSheet(f"""
                background-color: {bg_color};
                color: #ffffff;
                font-weight: bold;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 11px;
            """)
            self.tools_layout.insertWidget(self.tools_layout.count() - 1, badge)

        if not self.tool_statuses.get("git", False):
            self.run_btn.setEnabled(False)
            self.run_btn.setToolTip("Git ist nicht im PATH verfügbar.")
            self.statusBar().showMessage("Warnung: Git wurde nicht gefunden.", 4000)
        else:
            self.run_btn.setEnabled(True)
            self.run_btn.setToolTip("")

    # ── Git Hooks Setup ─────────────────────────────────────────────────────

    def _populate_git_hooks(self):
        """Discovers and displays available git hooks with tooltips."""
        while self.git_hooks_list_layout.count():
            item = self.git_hooks_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.hook_checkboxes.clear()

        available_hooks = self.template_manager.get_available_hooks()
        for hook in available_hooks:
            hook_id = hook["id"]
            cb = QCheckBox(f"{hook['name']} ({hook_id})")
            cb.setToolTip(hook["description"])
            cb.setChecked(hook.get("default", True))
            self.git_hooks_list_layout.addWidget(cb)
            self.hook_checkboxes[hook_id] = cb

    # ── Agenten-Regeln & Skills ─────────────────────────────────────────────

    def _refresh_agent_configs(self):
        """Populates rule and skill checkboxes and sets recommended defaults."""
        while self.agent_rules_layout.count():
            item = self.agent_rules_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        while self.agent_skills_layout.count():
            item = self.agent_skills_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.agent_rule_checkboxes.clear()
        self.agent_skill_checkboxes.clear()

        template_id = self.template_combo.currentData() or ""
        template_meta = self.template_manager.templates.get(template_id, {})
        language = template_meta.get("language", "")

        manifest = self.template_manager.get_agent_manifest()
        recommendations = self.template_manager.get_recommended_agent_configs(template_id, language)
        recommended_rules = set(recommendations.get("rules", []))
        recommended_skills = set(recommendations.get("skills", []))

        # Rules checkboxes
        for rule in manifest.get("rules", []):
            r_id = rule.get("id")
            cb = QCheckBox(f"{rule.get('name')}  –  {rule.get('description')}")
            cb.setToolTip(rule.get("description"))
            cb.setChecked(r_id in recommended_rules)
            self.agent_rules_layout.addWidget(cb)
            self.agent_rule_checkboxes[r_id] = cb

        # Skills checkboxes
        for skill in manifest.get("skills", []):
            s_id = skill.get("id")
            cb = QCheckBox(f"{skill.get('name')}  –  {skill.get('description')}")
            cb.setToolTip(skill.get("description"))
            cb.setChecked(s_id in recommended_skills)
            self.agent_skills_layout.addWidget(cb)
            self.agent_skill_checkboxes[s_id] = cb

    # ── Benutzerdefinierte Skripte ──────────────────────────────────────────

    def _add_custom_script(self):
        name = self.script_name_input.text().strip()
        cmd = self.script_cmd_input.text().strip()
        if not name or not cmd:
            return

        row = self.scripts_table.rowCount()
        self.scripts_table.insertRow(row)
        self.scripts_table.setItem(row, 0, QTableWidgetItem(name))
        self.scripts_table.setItem(row, 1, QTableWidgetItem(cmd))
        self.script_name_input.clear()
        self.script_cmd_input.clear()
        self._save_scripts_settings()

    def _remove_custom_script(self):
        row = self.scripts_table.currentRow()
        if row >= 0:
            self.scripts_table.removeRow(row)
            self._save_scripts_settings()

    def _get_custom_scripts_dict(self) -> dict[str, str]:
        scripts = {}
        for row in range(self.scripts_table.rowCount()):
            name_item = self.scripts_table.item(row, 0)
            cmd_item = self.scripts_table.item(row, 1)
            if name_item and cmd_item:
                scripts[name_item.text()] = cmd_item.text()
        return scripts

    def _save_scripts_settings(self):
        scripts = self._get_custom_scripts_dict()
        self.settings.setValue("custom_scripts", json.dumps(scripts))

    def _load_scripts_settings(self):
        raw = self.settings.value("custom_scripts", "{}")
        try:
            scripts = json.loads(raw) if isinstance(raw, str) else {}
            self.scripts_table.setRowCount(0)
            for name, cmd in scripts.items():
                row = self.scripts_table.rowCount()
                self.scripts_table.insertRow(row)
                self.scripts_table.setItem(row, 0, QTableWidgetItem(str(name)))
                self.scripts_table.setItem(row, 1, QTableWidgetItem(str(cmd)))
        except Exception:
            pass

    # ── Template Management ─────────────────────────────────────────────────

    def _populate_templates(self):
        current_selection = self.template_combo.currentData()
        self.template_combo.clear()
        for t_id, meta in self.template_manager.templates.items():
            label = f"{meta.get('name', t_id)} ({meta.get('language', 'Universal')})"
            self.template_combo.addItem(label, t_id)

        # Restore saved template if available
        saved_template = self.settings.value("last_template", "")
        target_to_select = current_selection or saved_template

        if target_to_select:
            idx = self.template_combo.findData(target_to_select)
            if idx >= 0:
                self.template_combo.setCurrentIndex(idx)

    def _reload_templates(self):
        """Reloads all templates from disk and updates the selection."""
        self.template_manager.reload_templates()
        self._populate_templates()
        self._on_template_changed()
        self._populate_git_hooks()
        self._refresh_agent_configs()
        count = len(self.template_manager.templates)
        self.statusBar().showMessage(f"{count} Vorlagen erfolgreich aktualisiert.", 3000)
        self.log_view.append(f"Vorlagen und Assets neu geladen ({count} Vorlagen gefunden).")

    def _open_templates_dir(self):
        """Opens the templates folder in the system file manager."""
        folder = self.default_templates_dir
        if not folder.exists():
            folder.mkdir(parents=True, exist_ok=True)
        self._open_directory(folder)

    def _open_hooks_dir(self):
        """Opens the hooks folder in the system file manager."""
        folder = self.template_manager.hooks_dir
        if not folder.exists():
            folder.mkdir(parents=True, exist_ok=True)
        self._open_directory(folder)

    def _open_agents_dir(self):
        """Opens the agent configs folder in the system file manager."""
        folder = self.template_manager.agent_configs_dir
        if not folder.exists():
            folder.mkdir(parents=True, exist_ok=True)
        self._open_directory(folder)

    def _add_custom_templates_dir(self):
        """Allows user to select a custom folder containing templates."""
        folder = QFileDialog.getExistingDirectory(self, "Zusätzlichen Vorlagen-Ordner auswählen")
        if folder:
            path_obj = Path(folder)
            self.template_manager.add_custom_dir(path_obj)

            custom_dirs_raw = self.settings.value("custom_templates_dirs", [])
            custom_list = list(custom_dirs_raw) if isinstance(custom_dirs_raw, list) else []
            if str(path_obj) not in custom_list:
                custom_list.append(str(path_obj))
                self.settings.setValue("custom_templates_dirs", custom_list)

            self._populate_templates()
            self._on_template_changed()
            QMessageBox.information(
                self,
                "Vorlagen-Ordner hinzugefügt",
                f"Der Ordner wurde registriert:\n{folder}\n\nVorlagen wurden neu geladen."
            )

    def _reset_custom_templates_dirs(self):
        """Resets custom templates directories to default."""
        self.settings.remove("custom_templates_dirs")
        self.template_manager = TemplateManager(self.default_templates_dir)
        self.generator = self.template_manager
        self._populate_templates()
        self._on_template_changed()
        QMessageBox.information(
            self,
            "Zurückgesetzt",
            "Alle zusätzlichen Vorlagen-Ordner wurden entfernt. Nur Standard-Vorlagen aktiv."
        )

    def _on_template_changed(self):
        while self.options_layout.count():
            item = self.options_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        self.option_checkboxes.clear()
        self.option_selects = {}

        template_id = self.template_combo.currentData()
        if not template_id:
            self.template_desc_label.setText("")
            return

        # Save selected template
        self.settings.setValue("last_template", template_id)

        template_meta = self.template_manager.templates.get(template_id, {})
        self.template_desc_label.setText(template_meta.get("description", ""))

        for opt in template_meta.get("options", []):
            opt_type = opt.get("type", "bool")
            opt_id = opt.get("id")

            if opt_type == "select":
                header = QLabel(f"<b>{opt.get('label', opt_id)}</b>")
                if opt.get("description"):
                    header.setToolTip(opt["description"])
                self.options_layout.addWidget(header)

                combo = QComboBox()
                default_val = opt.get("default", "")
                default_idx = 0
                for i, choice in enumerate(opt.get("choices", [])):
                    combo.addItem(choice["label"], choice["value"])
                    combo.setItemData(i, choice.get("description", ""), 3)
                    if choice["value"] == default_val:
                        default_idx = i
                combo.setCurrentIndex(default_idx)

                desc_label = QLabel()
                desc_label.setObjectName("mutedLabel")
                desc_label.setWordWrap(True)

                def _update(idx, lbl=desc_label, c=combo, choices=opt.get("choices", [])):
                    desc = choices[idx].get("description", "") if idx < len(choices) else ""
                    lbl.setText(desc)
                    c.setToolTip(desc)

                combo.currentIndexChanged.connect(_update)
                _update(default_idx)

                self.options_layout.addWidget(combo)
                self.options_layout.addWidget(desc_label)
                self.option_selects[opt_id] = combo

            else:  # bool (Checkbox)
                cb = QCheckBox(opt.get("label", opt_id))
                cb.setChecked(opt.get("default", False))
                if opt.get("description"):
                    cb.setToolTip(opt["description"])
                self.options_layout.addWidget(cb)
                self.option_checkboxes[opt_id] = cb

        # Update recommended agent configs for the new template
        self._refresh_agent_configs()

    # ── Einstellungen Persistenz ────────────────────────────────────────────

    def _load_saved_settings(self):
        """Restores previous window geometry, state, and paths from QSettings."""
        geom = self.settings.value("geometry")
        if isinstance(geom, QByteArray):
            self.restoreGeometry(geom)

        state = self.settings.value("windowState")
        if isinstance(state, QByteArray):
            self.restoreState(state)

        # Fullscreen state
        if self.settings.value("fullscreen", False, type=bool):
            self.showFullScreen()
            self.fullscreen_action.setChecked(True)

        # Restore last base path
        last_path = self.settings.value("last_path", "")
        if last_path and Path(last_path).is_dir():
            self.path_input.setText(last_path)
        else:
            default_path = str(Path.home() / "Documents")
            self.path_input.setText(default_path)

        # Restore author, email, license
        self.author_input.setText(self.settings.value("author_name", ""))
        self.email_input.setText(self.settings.value("author_email", ""))
        saved_license = self.settings.value("license", "MIT")
        idx = self.license_combo.findText(saved_license)
        if idx >= 0:
            self.license_combo.setCurrentIndex(idx)

        # Restore scripts
        self._load_scripts_settings()

    def _save_path_setting(self, text: str):
        cleaned = text.strip()
        if cleaned:
            self.settings.setValue("last_path", cleaned)

    def closeEvent(self, event):
        """Saves window geometry and active settings when closing."""
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("windowState", self.saveState())
        self.settings.setValue("fullscreen", self.isFullScreen())
        self.settings.setValue("last_path", self.path_input.text().strip())
        self.settings.setValue("author_name", self.author_input.text().strip())
        self.settings.setValue("author_email", self.email_input.text().strip())
        self.settings.setValue("license", self.license_combo.currentText())
        self._save_scripts_settings()
        current_tpl = self.template_combo.currentData()
        if current_tpl:
            self.settings.setValue("last_template", current_tpl)
        super().closeEvent(event)

    # ── Pfadauswahl ─────────────────────────────────────────────────────────

    def _select_path(self):
        current_val = self.path_input.text().strip()
        start_dir = current_val if Path(current_val).is_dir() else str(Path.home())
        folder = QFileDialog.getExistingDirectory(self, "Basis-Zielordner auswählen", start_dir)
        if folder:
            self.path_input.setText(folder)

    # ── Generierung & Abbruch ───────────────────────────────────────────────

    def _start_generation(self):
        name = self.name_input.text().strip()
        base_path_str = self.path_input.text().strip()
        template_id = self.template_combo.currentData()

        if not name or not base_path_str or not template_id:
            self.log_view.append("Fehler: Bitte Name, Pfad und Vorlage angeben.")
            self.statusBar().showMessage("Fehler: Unvollständige Eingaben.", 3000)
            return

        if not _VALID_NAME.match(name):
            self.log_view.append(
                "Fehler: Ungültiger Projektname. "
                "Nur Buchstaben, Ziffern, - und _ erlaubt, muss mit Buchstabe beginnen."
            )
            self.statusBar().showMessage("Fehler: Ungültiger Projektname.", 3000)
            return

        target_dir = Path(base_path_str) / name
        if target_dir.exists() and any(target_dir.iterdir()):
            self.log_view.append(f"Fehler: '{target_dir}' existiert bereits und ist nicht leer.")
            QMessageBox.warning(
                self,
                "Zielordner nicht leer",
                f"Das Verzeichnis '{target_dir}' existiert bereits und ist nicht leer.\n"
                "Bitte wähle einen anderen Namen oder leere das Verzeichnis."
            )
            return

        template_meta = self.template_manager.templates.get(template_id, {})
        license_val = self.license_combo.currentText()
        if license_val == "Keine":
            license_val = ""

        context = {
            "project_name": name,
            "project_slug": name.lower().replace("-", "_").replace(" ", "_"),
            "description": self.desc_input.text().strip(),
            "language": template_meta.get("language", ""),
            "author": self.author_input.text().strip(),
            "author_email": self.email_input.text().strip(),
            "license": license_val,
            "custom_scripts": self._get_custom_scripts_dict(),
            "enable_git_hooks": self.git_hooks_enable_cb.isChecked(),
            "selected_git_hooks": [
                h_id for h_id, cb in self.hook_checkboxes.items() if cb.isChecked()
            ],
            "enable_agent_configs": self.agent_configs_enable_cb.isChecked(),
            "selected_agent_rules": [
                r_id for r_id, cb in self.agent_rule_checkboxes.items() if cb.isChecked()
            ],
            "selected_agent_skills": [
                s_id for s_id, cb in self.agent_skill_checkboxes.items() if cb.isChecked()
            ],
        }

        for opt_id, cb in self.option_checkboxes.items():
            context[opt_id] = cb.isChecked()
        for opt_id, combo in self.option_selects.items():
            context[opt_id] = combo.currentData()

        # Update UI states for running generation
        self.run_btn.setEnabled(False)
        self.cancel_btn.setVisible(True)
        self.cancel_btn.setEnabled(True)
        self.cancel_btn.setText("✖  Abbrechen")
        self.open_btn.setVisible(False)
        self.log_view.clear()
        self.log_view.append(f"Starte Initialisierung von '{name}'...")
        self.statusBar().showMessage(f"Erstelle Projekt '{name}'...", 0)

        self.worker = GenerateWorker(self.generator, target_dir, template_id, context)
        self.worker.log_signal.connect(self.log_view.append)
        self.worker.finished_signal.connect(self._on_generation_finished)
        self.worker.start()

    def _cancel_generation(self):
        """Cancels running background generation."""
        if self.worker and self.worker.isRunning():
            self.cancel_btn.setEnabled(False)
            self.cancel_btn.setText("Breche ab...")
            self.log_view.append("⏳ Abbruch angefordert...")
            self.worker.cancel()

    def _on_generation_finished(self, ok: bool, target_dir_str: str, was_cancelled: bool):
        """Handles completion of generation worker."""
        self.run_btn.setEnabled(self.tool_statuses.get("git", False))
        self.cancel_btn.setVisible(False)

        if was_cancelled:
            self.statusBar().showMessage("Vorgang abgebrochen.", 4000)
            self.open_btn.setVisible(False)
            QMessageBox.information(
                self,
                "Vorgang abgebrochen",
                "Die Initialisierung wurde wie gewünscht abgebrochen."
            )
        elif ok:
            self._last_target_dir = target_dir_str
            self.log_view.append(f"\n✔ Projekt erfolgreich erstellt: {target_dir_str}")
            self.open_btn.setVisible(True)
            self.statusBar().showMessage(f"Projekt erfolgreich erstellt in {target_dir_str}", 6000)
            QMessageBox.information(
                self,
                "Projekt erstellt",
                f"✔ Projekt erfolgreich initialisiert!\n\n{target_dir_str}",
            )
        else:
            self.log_view.append("\n✖ Initialisierung fehlgeschlagen. Siehe Log oben.")
            self.statusBar().showMessage("Fehler bei der Initialisierung.", 5000)
            self.open_btn.setVisible(False)

    # ── Dateimanager / Explorer ─────────────────────────────────────────────

    def _open_in_explorer(self):
        if not self._last_target_dir:
            return
        path = Path(self._last_target_dir)
        if not path.is_dir():
            QMessageBox.warning(self, "Nicht gefunden", f"Verzeichnis nicht mehr vorhanden:\n{path}")
            return
        self._open_directory(path)

    def _open_directory(self, path: Path):
        """Opens a folder in the native platform file manager."""
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    # ── Über-Dialog ─────────────────────────────────────────────────────────

    def _show_about_dialog(self):
        QMessageBox.about(
            self,
            "Über Project Scaffolder",
            "<h3>Project Scaffolder</h3>"
            "<p>Ein modernes Werkzeug zur Initialisierung von Programmierprojekten mit Jinja2-Vorlagen.</p>"
            "<p><b>Funktionen:</b></p>"
            "<ul>"
            "<li>Unterstützt Python (CLI, FastAPI, GUI), Rust (CLI, GUI) und Node/TypeScript</li>"
            "<li>Optimierte Pipeline: uv init → uv venv → git init mit Git-Hooks (SemVer, Changelog)</li>"
            "<li>Modulare Generierung von Coding-Agent-Regeln und Skills (.agents/ & AGENTS.md)</li>"
            "<li>Konfigurierbare Autoren-, Lizenz- und Script-Metadaten</li>"
            "<li>Vollbildmodus (F11) und Fenstermodus mit Theme-Unterstützung</li>"
            "<li>Persistente Einstellungen mit QSettings</li>"
            "<li>Abbruch laufender Erstellungen</li>"
            "</ul>"
            "<p>© 2026 Daniel Rösch</p>"
        )


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())