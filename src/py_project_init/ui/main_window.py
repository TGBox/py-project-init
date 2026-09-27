import re
import sys
import shutil
from pathlib import Path
from PySide6.QtCore import QThread, Signal, QSettings, QByteArray, QUrl
from PySide6.QtGui import QAction, QKeySequence, QDesktopServices
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QComboBox, QCheckBox, QPushButton, QTextEdit,
    QFileDialog, QLabel, QGroupBox, QMessageBox
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
        self.resize(760, 800)

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
        self._last_target_dir: str = ""
        self.worker: GenerateWorker | None = None

        self._init_menu()
        self._init_ui()
        self._apply_theme()
        self._load_saved_settings()
        self._refresh_tool_status()
        self._populate_templates()

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
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(10)
        layout.setContentsMargins(14, 14, 14, 14)

        # 1. CLI Tools Statusleiste
        tools_group = QGroupBox("CLI-Tool Status (im System-PATH)")
        self.tools_layout = QHBoxLayout(tools_group)
        refresh_tools_btn = QPushButton("Neu prüfen")
        refresh_tools_btn.setObjectName("toolButton")
        refresh_tools_btn.clicked.connect(self._refresh_tool_status)
        self.tools_layout.addWidget(refresh_tools_btn)
        self.tools_layout.addStretch()
        layout.addWidget(tools_group)

        # 2. Metadaten
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

        # 3. Zielverzeichnis
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

        # 4. Template & Beschreibung
        lbl_tpl = QLabel("Projekt-Vorlage:")
        lbl_tpl.setObjectName("formLabel")

        tpl_header_layout = QHBoxLayout()
        tpl_header_layout.addWidget(lbl_tpl)
        tpl_header_layout.addStretch()

        reload_tpl_btn = QPushButton("🔄 Neu laden")
        reload_tpl_btn.setObjectName("toolButton")
        reload_tpl_btn.setToolTip("Vorlagen neu einlesen (z. B. nach Hinzufügen eigener Ordner)")
        reload_tpl_btn.clicked.connect(self._reload_templates)
        tpl_header_layout.addWidget(reload_tpl_btn)

        open_tpl_btn = QPushButton("📁 Vorlagen-Ordner")
        open_tpl_btn.setObjectName("toolButton")
        open_tpl_btn.setToolTip("Vorlagen-Verzeichnis im System-Explorer öffnen")
        open_tpl_btn.clicked.connect(self._open_templates_dir)
        tpl_header_layout.addWidget(open_tpl_btn)

        self.template_combo = QComboBox()
        self.template_combo.currentIndexChanged.connect(self._on_template_changed)
        self.template_desc_label = QLabel()
        self.template_desc_label.setObjectName("mutedLabel")
        self.template_desc_label.setWordWrap(True)

        self.options_box = QGroupBox("Zusatzoptionen")
        self.options_layout = QVBoxLayout(self.options_box)

        # 5. Buttons & Log
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

        layout.addWidget(lbl_name)
        layout.addWidget(self.name_input)
        layout.addWidget(self.name_error_label)
        layout.addWidget(lbl_desc)
        layout.addWidget(self.desc_input)
        layout.addWidget(lbl_path)
        layout.addLayout(path_layout)
        layout.addLayout(tpl_header_layout)
        layout.addWidget(self.template_combo)
        layout.addWidget(self.template_desc_label)
        layout.addWidget(self.options_box)
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
        count = len(self.template_manager.templates)
        self.statusBar().showMessage(f"{count} Vorlagen erfolgreich aktualisiert.", 3000)
        self.log_view.append(f"Vorlagen neu geladen ({count} Vorlagen gefunden).")

    def _open_templates_dir(self):
        """Opens the templates folder in the system file manager."""
        folder = self.default_templates_dir
        if not folder.exists():
            folder.mkdir(parents=True, exist_ok=True)
        self._open_directory(folder)

    def _add_custom_templates_dir(self):
        """Allows user to select a custom folder containing templates."""
        folder = QFileDialog.getExistingDirectory(self, "Zusätzlichen Vorlagen-Ordner auswählen")
        if folder:
            path_obj = Path(folder)
            self.template_manager.add_custom_dir(path_obj)

            # Persist custom dirs
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
        context = {
            "project_name": name,
            "project_slug": name.lower().replace("-", "_").replace(" ", "_"),
            "description": self.desc_input.text().strip(),
            "language": template_meta.get("language", ""),
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
            "<li>Automatische Git-Initialisierung und Post-Hooks</li>"
            "<li>Vollbildmodus (F11) und Fenstermodus</li>"
            "<li>Persistente Einstellungen mit QSettings</li>"
            "<li>Benutzerdefinierte Vorlagenordner und Vorlagen-Reload</li>"
            "<li>Abbruch laufender Erstellungen</li>"
            "</ul>"
            "<p>© 2026 Daniel Rösch</p>"
        )


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())