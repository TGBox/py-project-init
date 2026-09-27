import sys
from PySide6.QtWidgets import QApplication
from py_project_init.ui.main_window import MainWindow


def main() -> None:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
