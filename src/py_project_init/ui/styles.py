"""Modern dark theme stylesheet for PySide6 GUI."""

DARK_THEME = """
/* Global Window & Font Settings */
QWidget {
    background-color: #1a1b26;
    color: #c0caf5;
    font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
    font-size: 13px;
    selection-background-color: #3d59a1;
    selection-color: #ffffff;
}

/* Menu Bar */
QMenuBar {
    background-color: #16161e;
    color: #a9b1d6;
    border-bottom: 1px solid #292e42;
    padding: 2px 4px;
}

QMenuBar::item {
    background: transparent;
    padding: 6px 10px;
    border-radius: 4px;
}

QMenuBar::item:selected {
    background-color: #24283b;
    color: #7aa2f7;
}

QMenu {
    background-color: #1f2335;
    color: #c0caf5;
    border: 1px solid #3b4261;
    border-radius: 6px;
    padding: 4px;
}

QMenu::item {
    padding: 6px 24px 6px 12px;
    border-radius: 4px;
}

QMenu::item:selected {
    background-color: #3d59a1;
    color: #ffffff;
}

QMenu::separator {
    height: 1px;
    background-color: #292e42;
    margin: 4px 6px;
}

/* Group Boxes */
QGroupBox {
    background-color: #24283b;
    border: 1px solid #2f354d;
    border-radius: 8px;
    margin-top: 14px;
    padding: 14px 12px 12px 12px;
    font-weight: 600;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 14px;
    padding: 0 6px;
    color: #7aa2f7;
    background-color: transparent;
}

/* Input Fields */
QLineEdit {
    background-color: #1a1b26;
    color: #c0caf5;
    border: 1px solid #3b4261;
    border-radius: 6px;
    padding: 7px 10px;
    font-size: 13px;
}

QLineEdit:focus {
    border: 1px solid #7aa2f7;
    background-color: #1f2335;
}

QLineEdit:disabled {
    background-color: #16161e;
    color: #565f89;
    border-color: #292e42;
}

/* Combo Boxes */
QComboBox {
    background-color: #1a1b26;
    color: #c0caf5;
    border: 1px solid #3b4261;
    border-radius: 6px;
    padding: 6px 10px;
    min-height: 24px;
}

QComboBox:focus, QComboBox:hover {
    border: 1px solid #7aa2f7;
}

QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 24px;
    border-left: 1px solid #3b4261;
    border-top-right-radius: 6px;
    border-bottom-right-radius: 6px;
}

QComboBox::down-arrow {
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid #7aa2f7;
    width: 0;
    height: 0;
}

QComboBox QAbstractItemView {
    background-color: #1f2335;
    color: #c0caf5;
    border: 1px solid #3b4261;
    border-radius: 6px;
    selection-background-color: #3d59a1;
    selection-color: #ffffff;
    padding: 4px;
}

/* Buttons */
QPushButton {
    background-color: #2f354d;
    color: #c0caf5;
    border: 1px solid #3b4261;
    border-radius: 6px;
    padding: 7px 16px;
    font-weight: 500;
}

QPushButton:hover {
    background-color: #3d4466;
    border-color: #7aa2f7;
    color: #ffffff;
}

QPushButton:pressed {
    background-color: #24283b;
}

QPushButton:disabled {
    background-color: #1c1d2b;
    color: #565f89;
    border-color: #282a3c;
}

/* Primary Action Button */
QPushButton#primaryButton {
    background-color: #3d59a1;
    color: #ffffff;
    border: 1px solid #7aa2f7;
    font-weight: 600;
}

QPushButton#primaryButton:hover {
    background-color: #486bbd;
    border-color: #89b4fa;
}

QPushButton#primaryButton:pressed {
    background-color: #304780;
}

QPushButton#primaryButton:disabled {
    background-color: #1e2238;
    color: #565f89;
    border-color: #2c324c;
}

/* Cancel Button */
QPushButton#cancelButton {
    background-color: #4c2838;
    color: #f7768e;
    border: 1px solid #f7768e;
    font-weight: 600;
}

QPushButton#cancelButton:hover {
    background-color: #633348;
    color: #ff9eaf;
}

QPushButton#cancelButton:pressed {
    background-color: #3a1e2a;
}

/* Success Button */
QPushButton#successButton {
    background-color: #223f38;
    color: #73daca;
    border: 1px solid #73daca;
    font-weight: 600;
}

QPushButton#successButton:hover {
    background-color: #2d554a;
    color: #9feade;
}

QPushButton#successButton:pressed {
    background-color: #1a312b;
}

/* Secondary Toolbar Buttons */
QPushButton#toolButton {
    padding: 5px 10px;
    font-size: 12px;
}

/* Checkboxes */
QCheckBox {
    spacing: 8px;
    color: #c0caf5;
}

QCheckBox::indicator {
    width: 17px;
    height: 17px;
    border-radius: 4px;
    border: 1px solid #3b4261;
    background-color: #1a1b26;
}

QCheckBox::indicator:hover {
    border-color: #7aa2f7;
}

QCheckBox::indicator:checked {
    background-color: #7aa2f7;
    border-color: #7aa2f7;
    image: none;
}

/* Log View (Terminal style) */
QTextEdit {
    background-color: #13141f;
    color: #9ece6a;
    font-family: 'Consolas', 'Cascadia Code', 'JetBrains Mono', 'Courier New', monospace;
    font-size: 12px;
    border: 1px solid #292e42;
    border-radius: 6px;
    padding: 8px;
}

/* Scroll Bars */
QScrollBar:vertical {
    background-color: #1a1b26;
    width: 10px;
    margin: 0;
    border-radius: 5px;
}

QScrollBar::handle:vertical {
    background-color: #3b4261;
    min-height: 24px;
    border-radius: 5px;
}

QScrollBar::handle:vertical:hover {
    background-color: #7aa2f7;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

QScrollBar:horizontal {
    background-color: #1a1b26;
    height: 10px;
    margin: 0;
    border-radius: 5px;
}

QScrollBar::handle:horizontal {
    background-color: #3b4261;
    min-width: 24px;
    border-radius: 5px;
}

QScrollBar::handle:horizontal:hover {
    background-color: #7aa2f7;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0;
}

/* Tooltips */
QToolTip {
    background-color: #1f2335;
    color: #c0caf5;
    border: 1px solid #3b4261;
    border-radius: 4px;
    padding: 6px;
    font-size: 12px;
}

/* Labels */
QLabel {
    color: #c0caf5;
}

QLabel#formLabel {
    font-weight: 600;
    color: #a9b1d6;
    margin-top: 6px;
}

QLabel#mutedLabel {
    color: #787c99;
    font-size: 11px;
}

/* Status Bar */
QStatusBar {
    background-color: #16161e;
    color: #787c99;
    border-top: 1px solid #292e42;
}

/* Tables */
QTableWidget {
    background-color: #1a1b26;
    color: #c0caf5;
    gridline-color: #292e42;
    border: 1px solid #3b4261;
    border-radius: 6px;
    selection-background-color: #3d59a1;
}

QHeaderView::section {
    background-color: #1f2335;
    color: #7aa2f7;
    padding: 4px 8px;
    border: 1px solid #292e42;
    font-weight: 600;
}

/* Tree Widget */
QTreeWidget {
    background-color: #1a1b26;
    color: #c0caf5;
    border: 1px solid #3b4261;
    border-radius: 6px;
    padding: 4px;
}

QTreeWidget::item {
    padding: 4px 6px;
    border-radius: 4px;
}

QTreeWidget::item:hover {
    background-color: #24283b;
}

QTreeWidget::item:selected {
    background-color: #3d59a1;
    color: #ffffff;
}

/* Splitter */
QSplitter::handle {
    background-color: #292e42;
    width: 3px;
    height: 3px;
}

QSplitter::handle:hover {
    background-color: #7aa2f7;
}

/* Dialogs */
QDialog {
    background-color: #1a1b26;
    color: #c0caf5;
}
"""
