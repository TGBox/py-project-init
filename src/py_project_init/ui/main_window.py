import sys
import shutil
from pathlib import Path
from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QComboBox, QCheckBox, QPushButton, QTextEdit,
    QFileDialog, QLabel, QGroupBox
)
from py_project_init.core.generator import TemplateManager, ProjectGenerator

CHECKED_TOOLS = ["git", "uv", "cargo", "npm"]

def check_cli_tool(tool_name: str) -> bool:
    return shutil.which(tool_name) is not None

class GenerateWorker(QThread):
    log_signal = Signal(str)
    finished_signal = Signal(bool)

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
            self.finished_signal.emit(True)
        except Exception as e:
            self.log_signal.emit(f"Fehler: {str(e)}")
            self.finished_signal.emit(False)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Project Scaffolder")
        self.resize(720, 720)

        base_dir = Path(__file__).resolve().parent.parent.parent.parent
        self.templates_dir = base_dir / "templates"
        self.template_manager = TemplateManager(self.templates_dir)
        self.generator = ProjectGenerator(self.template_manager)

        self.tool_statuses: dict[str, bool] = {}
        self.option_checkboxes: dict[str, QCheckBox] = {}

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
        self.name_input.setPlaceholderText("z. B. my-super-service")
        self.desc_input = QLineEdit()
        self.desc_input.setPlaceholderText("Kurze Beschreibung des Projekts")

        # 3. Zielverzeichnis
        path_layout = QHBoxLayout()
        self.path_input = QLineEdit()
        browse_btn = QPushButton("Zielordner wählen...")
        browse_btn.clicked.connect(self._select_path)
        path_layout.addWidget(self.path_input)
        path_layout.addWidget(browse_btn)

        # 4. Template & dynamische Optionen
        self.template_combo = QComboBox()
        self.template_combo.currentIndexChanged.connect(self._on_template_changed)
        self.options_box = QGroupBox("Zusatzoptionen")
        self.options_layout = QVBoxLayout(self.options_box)

        # 5. Start-Button & Log
        self.run_btn = QPushButton("Projekt initialisieren")
        self.run_btn.clicked.connect(self._start_generation)
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)

        layout.addWidget(QLabel("Projektname:"))
        layout.addWidget(self.name_input)
        layout.addWidget(QLabel("Beschreibung:"))
        layout.addWidget(self.desc_input)
        layout.addWidget(QLabel("Speicherort:"))
        layout.addLayout(path_layout)
        layout.addWidget(QLabel("Projekt-Vorlage:"))
        layout.addWidget(self.template_combo)
        layout.addWidget(self.options_box)
        layout.addWidget(self.run_btn)
        layout.addWidget(QLabel("Status / Ausführungsprotokoll:"))
        layout.addWidget(self.log_view)

    def _refresh_tool_status(self):
        # Alte Badges entfernen (außer dem Refresh-Button)
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

        # Git zwingend erforderlich
        if not self.tool_statuses.get("git", False):
            self.run_btn.setEnabled(False)
            self.run_btn.setToolTip("Git ist nicht im PATH verfügbar.")
        else:
            self.run_btn.setEnabled(True)
            self.run_btn.setToolTip("")

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
        self.option_selects: dict[str, QComboBox] = {}

        template_id = self.template_combo.currentData()
        if not template_id:
            return

        template_meta = self.template_manager.templates.get(template_id, {})
        for opt in template_meta.get("options", []):
            opt_type = opt.get("type", "bool")
            opt_id = opt.get("id")

            if opt_type == "select":
                # Label + Beschreibungstext
                header = QLabel(f"<b>{opt.get('label', opt_id)}</b>")
                if opt.get("description"):
                    header.setToolTip(opt["description"])
                self.options_layout.addWidget(header)

                combo = QComboBox()
                combo.setToolTip(opt.get("description", ""))
                default_val = opt.get("default", "")
                default_idx = 0
                for i, choice in enumerate(opt.get("choices", [])):
                    combo.addItem(choice["label"], choice["value"])
                    # Beschreibung als Tooltip des jeweiligen Eintrags
                    combo.setItemData(i, choice.get("description", ""), 3)  # Qt.ToolTipRole = 3
                    if choice["value"] == default_val:
                        default_idx = i
                combo.setCurrentIndex(default_idx)

                # Tooltip beim Wechsel der Auswahl aktualisieren
                def _update_tooltip(idx, c=combo, choices=opt.get("choices", [])):
                    desc = choices[idx].get("description", "") if idx < len(choices) else ""
                    c.setToolTip(desc)

                combo.currentIndexChanged.connect(_update_tooltip)
                _update_tooltip(default_idx)

                # Beschreibung des aktuell gewählten Eintrags als Label anzeigen
                desc_label = QLabel()
                desc_label.setWordWrap(True)
                desc_label.setStyleSheet("color: #888; font-size: 11px; margin-bottom: 4px;")

                def _update_desc(idx, lbl=desc_label, choices=opt.get("choices", [])):
                    lbl.setText(choices[idx].get("description", "") if idx < len(choices) else "")

                combo.currentIndexChanged.connect(_update_desc)
                _update_desc(default_idx)

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

    def _select_path(self):
        folder = QFileDialog.getExistingDirectory(self, "Basis-Zielordner auswählen")
        if folder:
            self.path_input.setText(folder)

    def _start_generation(self):
        name = self.name_input.text().strip()
        base_path_str = self.path_input.text().strip()
        template_id = self.template_combo.currentData()

        if not name or not base_path_str or not template_id:
            self.log_view.append("Fehler: Bitte Name, Pfad und Vorlage angeben.")
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
        for opt_id, combo in getattr(self, "option_selects", {}).items():
            context[opt_id] = combo.currentData()

        self.run_btn.setEnabled(False)
        self.log_view.clear()
        self.log_view.append(f"Starte Initialisierung von '{name}'...")

        self.worker = GenerateWorker(self.generator, target_dir, template_id, context)
        self.worker.log_signal.connect(self.log_view.append)
        self.worker.finished_signal.connect(lambda ok: self.run_btn.setEnabled(self.tool_statuses.get("git", False)))
        self.worker.start()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())