"""Dialogs for project preview, retrofit mode, and template creation."""

import os
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTreeWidget, QTreeWidgetItem, QTextEdit, QSplitter,
    QFileDialog, QGroupBox, QCheckBox, QLineEdit, QComboBox,
    QMessageBox
)
from py_project_init.core.generator import TemplateManager


class PreviewDialog(QDialog):
    """Dialog displaying a virtual preview of generated files and folders."""

    def __init__(self, files_map: dict[str, str], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Live-Vorschau: Projektstruktur & Dateien")
        self.resize(920, 620)
        self.files_map = files_map

        self._init_ui()
        self._populate_tree()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(14, 14, 14, 14)

        info_label = QLabel(
            "<b>Virtuelle Vorschau:</b> Alle Dateien werden simuliert gerendert, "
            "ohne das Dateisystem zu verändern."
        )
        info_label.setObjectName("mutedLabel")
        layout.addWidget(info_label)

        splitter = QSplitter(Qt.Horizontal)

        # Left: Tree Widget
        tree_container = QVBoxLayout()
        tree_label = QLabel("<b>Projektstruktur</b>")
        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderLabels(["Datei / Ordner"])
        self.tree_widget.setColumnWidth(0, 280)
        self.tree_widget.itemSelectionChanged.connect(self._on_item_selected)

        tree_layout_widget = QTreeWidget()  # reuse splitter widgets cleanly
        splitter.addWidget(self.tree_widget)

        # Right: File Content Preview
        content_container = QGroupBox("Dateiinhalt")
        content_layout = QVBoxLayout(content_container)
        self.file_title_label = QLabel("<i>Keine Datei ausgewählt</i>")
        self.file_title_label.setStyleSheet("font-weight: 600; color: #7aa2f7;")
        self.content_view = QTextEdit()
        self.content_view.setReadOnly(True)
        self.content_view.setPlaceholderText(
            "Wähle links eine Datei aus, um deren Inhalt anzuzeigen..."
        )

        content_layout.addWidget(self.file_title_label)
        content_layout.addWidget(self.content_view)
        splitter.addWidget(content_container)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        layout.addWidget(splitter)

        # Footer
        footer_layout = QHBoxLayout()
        count = len(self.files_map)
        count_label = QLabel(f"<b>{count}</b> Datei{'en' if count != 1 else ''} insgesamt generiert")
        count_label.setObjectName("mutedLabel")

        close_btn = QPushButton("Schließen")
        close_btn.clicked.connect(self.accept)

        footer_layout.addWidget(count_label)
        footer_layout.addStretch()
        footer_layout.addWidget(close_btn)
        layout.addLayout(footer_layout)

    def _populate_tree(self):
        """Builds a hierarchical tree from flat relative paths."""
        self.tree_widget.clear()
        nodes: dict[str, QTreeWidgetItem] = {}

        # Sort paths so parent folders are processed before files
        sorted_paths = sorted(self.files_map.keys())

        for rel_path in sorted_paths:
            parts = rel_path.split("/")
            current_path = ""
            parent_item = None

            for i, part in enumerate(parts):
                current_path = f"{current_path}/{part}" if current_path else part
                is_file = (i == len(parts) - 1)

                if current_path in nodes:
                    parent_item = nodes[current_path]
                else:
                    item = QTreeWidgetItem()
                    if is_file:
                        item.setText(0, f"📄 {part}")
                        item.setData(0, Qt.UserRole, rel_path)
                    else:
                        item.setText(0, f"📁 {part}")
                        item.setData(0, Qt.UserRole, None)

                    if parent_item is None:
                        self.tree_widget.addTopLevelItem(item)
                    else:
                        parent_item.addChild(item)

                    nodes[current_path] = item
                    parent_item = item

        self.tree_widget.expandAll()

        # Select first file if available
        for i in range(self.tree_widget.topLevelItemCount()):
            top = self.tree_widget.topLevelItem(i)
            first_file = self._find_first_file_item(top)
            if first_file:
                self.tree_widget.setCurrentItem(first_file)
                break

    def _find_first_file_item(self, item: QTreeWidgetItem) -> QTreeWidgetItem | None:
        if item.data(0, Qt.UserRole):
            return item
        for i in range(item.childCount()):
            res = self._find_first_file_item(item.child(i))
            if res:
                return res
        return None

    def _on_item_selected(self):
        selected = self.tree_widget.selectedItems()
        if not selected:
            self.file_title_label.setText("<i>Keine Datei ausgewählt</i>")
            self.content_view.clear()
            return

        item = selected[0]
        rel_path = item.data(0, Qt.UserRole)
        if rel_path and rel_path in self.files_map:
            content = self.files_map[rel_path]
            lines = content.count("\n") + 1
            size_bytes = len(content.encode("utf-8"))
            self.file_title_label.setText(f"📄 {rel_path}  ({lines} Zeilen, {size_bytes} Bytes)")
            self.content_view.setPlainText(content)
        else:
            self.file_title_label.setText(f"📁 {item.text(0).replace('📁 ', '')} (Ordner)")
            self.content_view.clear()


class RetrofitDialog(QDialog):
    """Dialog to retrofit Git hooks and agent configs to an existing project."""

    def __init__(self, template_manager: TemplateManager, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Bestehendes Projekt nachrüsten")
        self.resize(680, 620)
        self.template_manager = template_manager
        self.hook_checkboxes: dict[str, QCheckBox] = {}
        self.rule_checkboxes: dict[str, QCheckBox] = {}
        self.skill_checkboxes: dict[str, QCheckBox] = {}

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(14, 14, 14, 14)

        # Target Directory
        target_group = QGroupBox("Zielprojekt (Bestehender Ordner)")
        target_layout = QHBoxLayout(target_group)
        self.target_path_input = QLineEdit()
        self.target_path_input.setPlaceholderText("Pfad zum bestehenden Projektordner auswählen...")
        browse_btn = QPushButton("Durchsuchen...")
        browse_btn.clicked.connect(self._select_target_dir)
        target_layout.addWidget(self.target_path_input)
        target_layout.addWidget(browse_btn)
        layout.addWidget(target_group)

        # Git Hooks Selection
        hooks_group = QGroupBox("Git Hooks nachrüsten (.git/hooks/)")
        hooks_layout = QVBoxLayout(hooks_group)
        self.enable_hooks_cb = QCheckBox("Git Hooks im Zielprojekt installieren")
        self.enable_hooks_cb.setChecked(True)
        hooks_layout.addWidget(self.enable_hooks_cb)

        hooks_list_layout = QVBoxLayout()
        for hook in self.template_manager.get_available_hooks():
            h_id = hook["id"]
            cb = QCheckBox(f"{hook['name']} ({h_id}) – {hook.get('description', '')}")
            cb.setChecked(hook.get("default", True))
            hooks_list_layout.addWidget(cb)
            self.hook_checkboxes[h_id] = cb

        self.enable_hooks_cb.toggled.connect(
            lambda checked: [cb.setEnabled(checked) for cb in self.hook_checkboxes.values()]
        )
        hooks_layout.addLayout(hooks_list_layout)
        layout.addWidget(hooks_group)

        # Agent Configs Selection
        agent_group = QGroupBox("Agent-Konfigurationen nachrüsten (.agents/ & AGENTS.md)")
        agent_layout = QVBoxLayout(agent_group)
        self.enable_agent_cb = QCheckBox("Agenten-Regeln & Skills installieren")
        self.enable_agent_cb.setChecked(True)
        agent_layout.addWidget(self.enable_agent_cb)

        manifest = self.template_manager.get_agent_manifest()

        # Rules
        lbl_rules = QLabel("<b>Regeln (.agents/rules/):</b>")
        agent_layout.addWidget(lbl_rules)
        for rule in manifest.get("rules", []):
            r_id = rule.get("id")
            cb = QCheckBox(f"{rule.get('name')} – {rule.get('description', '')}")
            cb.setChecked(True)
            agent_layout.addWidget(cb)
            self.rule_checkboxes[r_id] = cb

        # Skills
        lbl_skills = QLabel("<b>Skills (.agents/skills/):</b>")
        agent_layout.addWidget(lbl_skills)
        for skill in manifest.get("skills", []):
            s_id = skill.get("id")
            cb = QCheckBox(f"{skill.get('name')} – {skill.get('description', '')}")
            cb.setChecked(True)
            agent_layout.addWidget(cb)
            self.skill_checkboxes[s_id] = cb

        self.enable_agent_cb.toggled.connect(
            lambda checked: (
                [cb.setEnabled(checked) for cb in self.rule_checkboxes.values()],
                [cb.setEnabled(checked) for cb in self.skill_checkboxes.values()]
            )
        )
        layout.addWidget(agent_group)

        # Log View
        lbl_log = QLabel("<b>Ausführungsprotokoll:</b>")
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumHeight(130)
        layout.addWidget(lbl_log)
        layout.addWidget(self.log_view)

        # Buttons
        btn_layout = QHBoxLayout()
        self.run_btn = QPushButton("▶ Nachrüsten starten")
        self.run_btn.setObjectName("primaryButton")
        self.run_btn.clicked.connect(self._run_retrofit)

        close_btn = QPushButton("Schließen")
        close_btn.clicked.connect(self.accept)

        btn_layout.addWidget(self.run_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

    def _select_target_dir(self):
        selected = QFileDialog.getExistingDirectory(self, "Bestehendes Projekt auswählen")
        if selected:
            self.target_path_input.setText(selected)

    def _run_retrofit(self):
        target_str = self.target_path_input.text().strip()
        if not target_str:
            QMessageBox.warning(self, "Eingabe fehlt", "Bitte wähle zuerst einen Zielordner aus.")
            return

        target_path = Path(target_str)
        if not target_path.is_dir():
            QMessageBox.warning(self, "Ungültiger Pfad", f"Der Ordner '{target_path}' existiert nicht.")
            return

        self.log_view.clear()
        self.log_view.append(f"Starte Nachrüstung für: {target_path}\n")

        # 1. Retrofit hooks
        if self.enable_hooks_cb.isChecked():
            selected_hooks = [h_id for h_id, cb in self.hook_checkboxes.items() if cb.isChecked()]
            if selected_hooks:
                self.template_manager.retrofit_hooks(
                    target_path, selected_hooks, log_callback=self.log_view.append
                )
            else:
                self.log_view.append("Keine Git Hooks ausgewählt.")

        # 2. Retrofit agent configs
        if self.enable_agent_cb.isChecked():
            selected_rules = [r_id for r_id, cb in self.rule_checkboxes.items() if cb.isChecked()]
            selected_skills = [s_id for s_id, cb in self.skill_checkboxes.items() if cb.isChecked()]
            if selected_rules or selected_skills:
                self.template_manager.retrofit_agent_configs(
                    target_path,
                    selected_rules=selected_rules,
                    selected_skills=selected_skills,
                    log_callback=self.log_view.append,
                )
            else:
                self.log_view.append("Keine Agenten-Regeln oder Skills ausgewählt.")

        self.log_view.append("\n✔ Nachrüstung abgeschlossen!")
        QMessageBox.information(self, "Erfolg", "Nachrüstung erfolgreich abgeschlossen!")


class CreateTemplateDialog(QDialog):
    """Dialog to create a new reusable template from an existing project directory."""

    def __init__(self, template_manager: TemplateManager, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Neue Vorlage aus bestehendem Projekt erstellen")
        self.resize(620, 520)
        self.template_manager = template_manager

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(14, 14, 14, 14)

        # Source Project Directory
        source_group = QGroupBox("Quell-Projektordner")
        source_layout = QHBoxLayout(source_group)
        self.source_path_input = QLineEdit()
        self.source_path_input.setPlaceholderText("Bestehenden Projektordner auswählen...")
        browse_btn = QPushButton("Durchsuchen...")
        browse_btn.clicked.connect(self._select_source_dir)
        source_layout.addWidget(self.source_path_input)
        source_layout.addWidget(browse_btn)
        layout.addWidget(source_group)

        # Template Metadata
        meta_group = QGroupBox("Vorlagen-Metadaten")
        meta_layout = QVBoxLayout(meta_group)

        lbl_id = QLabel("Vorlagen-ID (Ordnername):")
        lbl_id.setObjectName("formLabel")
        self.id_input = QLineEdit()
        self.id_input.setPlaceholderText("z. B. python-data-pipeline (Kleinbuchstaben, Bindestrich)")

        lbl_lang = QLabel("Programmiersprache:")
        lbl_lang.setObjectName("formLabel")
        self.lang_combo = QComboBox()
        self.lang_combo.addItems(["Python", "Rust", "Node / TypeScript", "Andere"])

        lbl_desc = QLabel("Beschreibung:")
        lbl_desc.setObjectName("formLabel")
        self.desc_input = QLineEdit()
        self.desc_input.setPlaceholderText("Kurzbeschreibung der neuen Vorlage...")

        meta_layout.addWidget(lbl_id)
        meta_layout.addWidget(self.id_input)
        meta_layout.addWidget(lbl_lang)
        meta_layout.addWidget(self.lang_combo)
        meta_layout.addWidget(lbl_desc)
        meta_layout.addWidget(self.desc_input)
        layout.addWidget(meta_group)

        # Log View
        lbl_log = QLabel("<b>Ausführungsprotokoll:</b>")
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumHeight(120)
        layout.addWidget(lbl_log)
        layout.addWidget(self.log_view)

        # Buttons
        btn_layout = QHBoxLayout()
        self.create_btn = QPushButton("✨ Vorlage erstellen")
        self.create_btn.setObjectName("primaryButton")
        self.create_btn.clicked.connect(self._run_create)

        close_btn = QPushButton("Schließen")
        close_btn.clicked.connect(self.accept)

        btn_layout.addWidget(self.create_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

    def _select_source_dir(self):
        selected = QFileDialog.getExistingDirectory(self, "Quell-Projektordner auswählen")
        if selected:
            self.source_path_input.setText(selected)
            if not self.id_input.text():
                folder_name = Path(selected).name.lower().replace(" ", "-")
                self.id_input.setText(folder_name)

    def _run_create(self):
        src_str = self.source_path_input.text().strip()
        tpl_name = self.id_input.text().strip()
        desc = self.desc_input.text().strip() or f"Vorlage basierend auf {tpl_name}"
        lang = self.lang_combo.currentText().lower()
        if "node" in lang:
            lang = "node"

        if not src_str or not tpl_name:
            QMessageBox.warning(
                self, "Eingabe fehlt", "Bitte Quellordner und Vorlagen-ID angeben."
            )
            return

        src_path = Path(src_str)
        if not src_path.is_dir():
            QMessageBox.warning(self, "Ungültiger Pfad", f"'{src_path}' ist kein Verzeichnis.")
            return

        out_dir = self.template_manager.default_templates_dir / tpl_name
        if out_dir.exists():
            res = QMessageBox.question(
                self,
                "Vorlage überschreiben?",
                f"Eine Vorlage mit dem Namen '{tpl_name}' existiert bereits. Überschreiben?",
                QMessageBox.Yes | QMessageBox.No
            )
            if res != QMessageBox.Yes:
                return

        self.log_view.clear()
        self.log_view.append(f"Erstelle Vorlage '{tpl_name}' in {out_dir}...")

        try:
            self.template_manager.create_template_from_project(
                source_dir=src_path,
                output_dir=out_dir,
                template_name=tpl_name,
                language=lang,
                description=desc,
                log_callback=self.log_view.append
            )
            self.template_manager.reload()
            self.log_view.append("\n✔ Vorlage erfolgreich erstellt und registriert!")
            QMessageBox.information(
                self, "Erfolg", f"Vorlage '{tpl_name}' wurde erfolgreich erstellt!"
            )
        except Exception as e:
            self.log_view.append(f"\nFehler: {e}")
            QMessageBox.critical(self, "Fehler", f"Erstellung fehlgeschlagen:\n{e}")
