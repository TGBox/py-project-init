import re
import sys
import shutil
import subprocess
from pathlib import Path
from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QComboBox, QCheckBox, QPushButton, QTextEdit,
    QFileDialog, QLabel, QGroupBox, QMessageBox
)
from py_project_init.core.generator import TemplateManager, ProjectGenerator

CHECKED_TOOLS = ["git", "uv", "cargo", "npm"]

# Erlaubte Zeichen im Projektnamen (Kleinbuchstaben, Ziffern, Bindestrich, Unterstrich)
_VALID_NAME = re.compile(r"^[a-zA-Z][a-zA-Z0-9_-]*$")


def check_cli_tool(tool_name: str) -> bool:
    return shutil.which(tool_name) is not None


class GenerateWorker(QThread):
    log_signal = Signal(str)
    finished_signal = Signal(bool, str)  # ok, target_dir_str

    def __init__(self, generator: ProjectGenerator, target_dir: Path, template_id: str, context: dict):
        super().__init__()
        self.generator = generator
        self.target_dir = target_dir
        self.template_id = template_id
        self.context = context

    def run(self):
        try:
            self.generator.generate(
                self.target_dir, self.template_id, self.context,
                log_callback=self.log_signal.emit
            )
            self.finished_signal.emit(True, str(self.target_dir))
        except Exception as e:
            self.log_signal.emit(f"Fehler: {str(e)}")
            self.finished_signal.emit(False, "")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Project Scaffolder")
        self.resize(720, 760)

        base_dir = Path(__file__).resolve().parent.parent.parent.parent
        self.templates_dir = base_dir / "templates"
        self.template_manager = TemplateManager(self.templates_dir)
        self.generator = ProjectGenerator(self.template_manager)

        self.tool_statuses: dict[str, bool] = {}
        self.option_checkboxes: dict[str, QCheckBox] = {}
        self.option_selects: dict[str, QComboBox] = {}
        self._last_target_dir: str = ""

        self._init_ui()
        self._refresh_tool_status()
        self._populate_templates()

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # 1. CLI Tools Statusleiste
        tools_group = QGroupBox("CLI-Tool Status (im System-PATH)")
        self.tools_layout = QHBoxLayout(tools_group)
        refresh_tools_btn = QPushButton("Neu prüfen")
        refresh_tools_btn.clicked.connect(self._refresh_tool_status)
        self.tools_layout.addWidget(refresh_tools_btn)
        self.tools_layout.addStretch()
        layout.addWidget(tools_group)

        # 2. Metadaten
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("z. B. my-super-service  (Buchstaben, Ziffern, - und _)")
        self.name_input.textChanged.connect(self._validate_name)
        self.name_error_label = QLabel()
        self.name_error_label.setStyleSheet("color: #e74c3c; font-size: 11px;")
        self.name_error_label.setVisible(False)

        self.desc_input = QLineEdit()
        self.desc_input.setPlaceholderText("Kurze Beschreibung des Projekts")

        # 3. Zielverzeichnis
        path_layout = QHBoxLayout()
        self.path_input = QLineEdit()
        browse_btn = QPushButton("Zielordner wählen...")
        browse_btn.clicked.connect(self._select_path)
        path_layout.addWidget(self.path_input)
        path_layout.addWidget(browse_btn)

        # 4. Template & Beschreibung
        self.template_combo = QComboBox()
        self.template_combo.currentIndexChanged.connect(self._on_template_changed)
        self.template_desc_label = QLabel()
        self.template_desc_label.setWordWrap(True)
        self.template_desc_label.setStyleSheet("color: #555; font-size: 11px; margin: 2px 0 6px 0;")

        self.options_box = QGroupBox("Zusatzoptionen")
        self.options_layout = QVBoxLayout(self.options_box)

        # 5. Start-Button, Erfolg-Button & Log
        btn_row = QHBoxLayout()
        self.run_btn = QPushButton("▶  Projekt initialisieren")
        self.run_btn.clicked.connect(self._start_generation)
        self.open_btn = QPushButton("📂  Im Explorer öffnen")
        self.open_btn.clicked.connect(self._open_in_explorer)
        self.open_btn.setVisible(False)
        btn_row.addWidget(self.run_btn)
        btn_row.addWidget(self.open_btn)

        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMinimumHeight(180)

        layout.addWidget(QLabel("Projektname:"))
        layout.addWidget(self.name_input)
        layout.addWidget(self.name_error_label)
        layout.addWidget(QLabel("Beschreibung:"))
        layout.addWidget(self.desc_input)
        layout.addWidget(QLabel("Speicherort:"))
        layout.addLayout(path_layout)
        layout.addWidget(QLabel("Projekt-Vorlage:"))
        layout.addWidget(self.template_combo)
        layout.addWidget(self.template_desc_label)
        layout.addWidget(self.options_box)
        layout.addLayout(btn_row)
        layout.addWidget(QLabel("Status / Ausführungsprotokoll:"))
        layout.addWidget(self.log_view)

    # ── Eingabevalidierung ──────────────────────────────────────────────────

    def _validate_name(self, text: str) -> bool:
        """Gibt True zurück wenn der Name gültig ist, zeigt sonst Fehlermeldung."""
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

    # ── Tool-Status ─────────────────────────────────────────────────────────

    def _refresh_tool_status(self):
        for i in reversed(range(1, self.tools_layout.count() - 1)):
            widget = self.tools_layout.takeAt(i).widget()
            if widget:
                widget.deleteLater()

        for tool in CHECKED_TOOLS:
            available = check_cli_tool(tool)
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
        else:
            self.run_btn.setEnabled(True)
            self.run_btn.setToolTip("")

    # ── Template-Auswahl ────────────────────────────────────────────────────

    def _populate_templates(self):
        self.template_combo.clear()
        for t_id, meta in self.template_manager.templates.items():
            label = f"{meta.get('name', t_id)} ({meta.get('language', 'Universal')})"
            self.template_combo.addItem(label, t_id)

    def _on_template_changed(self):
        # Alle alten Widgets entfernen
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

        template_meta = self.template_manager.templates.get(template_id, {})

        # Template-Beschreibung anzeigen (Punkt 9)
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
                desc_label.setWordWrap(True)
                desc_label.setStyleSheet("color: #888; font-size: 11px; margin-bottom: 4px;")

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

    # ── Pfad wählen ─────────────────────────────────────────────────────────

    def _select_path(self):
        folder = QFileDialog.getExistingDirectory(self, "Basis-Zielordner auswählen")
        if folder:
            self.path_input.setText(folder)

    # ── Generierung ─────────────────────────────────────────────────────────

    def _start_generation(self):
        name = self.name_input.text().strip()
        base_path_str = self.path_input.text().strip()
        template_id = self.template_combo.currentData()

        # Eingabevalidierung (Punkt 6)
        if not name or not base_path_str or not template_id:
            self.log_view.append("Fehler: Bitte Name, Pfad und Vorlage angeben.")
            return
        if not _VALID_NAME.match(name):
            self.log_view.append(
                "Fehler: Ungültiger Projektname. "
                "Nur Buchstaben, Ziffern, - und _ erlaubt, muss mit Buchstabe beginnen."
            )
            return

        target_dir = Path(base_path_str) / name
        if target_dir.exists() and any(target_dir.iterdir()):
            self.log_view.append(f"Fehler: '{target_dir}' existiert bereits und ist nicht leer.")
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

        self.run_btn.setEnabled(False)
        self.open_btn.setVisible(False)
        self.log_view.clear()
        self.log_view.append(f"Starte Initialisierung von '{name}'...")

        self.worker = GenerateWorker(self.generator, target_dir, template_id, context)
        self.worker.log_signal.connect(self.log_view.append)
        self.worker.finished_signal.connect(self._on_generation_finished)
        self.worker.start()

    def _on_generation_finished(self, ok: bool, target_dir_str: str):
        """Erfolgsmeldung + Explorer-Button anzeigen (Punkt 5)."""
        self.run_btn.setEnabled(self.tool_statuses.get("git", False))
        if ok:
            self._last_target_dir = target_dir_str
            self.log_view.append(f"\n✔ Projekt erfolgreich erstellt: {target_dir_str}")
            self.open_btn.setVisible(True)
            QMessageBox.information(
                self,
                "Projekt erstellt",
                f"✔ Projekt erfolgreich initialisiert!\n\n{target_dir_str}",
            )
        else:
            self.log_view.append("\n✖ Initialisierung fehlgeschlagen. Siehe Log oben.")
            self.open_btn.setVisible(False)

    def _open_in_explorer(self):
        """Öffnet das erstellte Projektverzeichnis im System-Dateimanager."""
        if not self._last_target_dir:
            return
        path = Path(self._last_target_dir)
        if not path.exists():
            QMessageBox.warning(self, "Nicht gefunden", f"Verzeichnis nicht mehr vorhanden:\n{path}")
            return
        if sys.platform == "win32":
            subprocess.Popen(["explorer", str(path)])
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())