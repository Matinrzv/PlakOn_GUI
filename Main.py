import sys
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QVBoxLayout,
    QWidget,
    QComboBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QHBoxLayout,
    QGridLayout,
    QTextEdit,
)
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QFileDialog, QMessageBox

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Test")
        self.resize(400,400)
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.page_layout = QVBoxLayout()
        central_widget.setLayout(self.page_layout)
        self.text_input = QTextEdit()
        self.text_input.setPlaceholderText("write anythings...")
        self.page_layout.addWidget(self.text_input)
        self._build_actions()
        self._build_menus()
        self._build_toolbar()
        self.statusBar().showMessage("Ready")
        self.text_input.textChanged.connect(self.on_text_changed)

    def _build_actions(self):
        self.new_action = QAction("New",self)
        self.exit_action = QAction("Exit",self)
        self.new_action.triggered.connect(self.text_input.clear)
        self.exit_action.triggered.connect(self.close)
        self.open_action = QAction("Open...", self)
        self.save_action = QAction("Save", self)
        self.open_action.triggered.connect(self.open_file)
        self.save_action.triggered.connect(self.save_file)


    def _build_menus(self):
        file_menu = self.menuBar().addMenu("File")
        file_menu.addAction(self.new_action)
        file_menu.addAction(self.open_action)
        file_menu.addAction(self.save_action)
        file_menu.addSeparator()
        file_menu.addAction(self.exit_action)

    def _build_toolbar(self):
        toolbar = self.addToolBar("Main")
        toolbar.addAction(self.new_action)
        toolbar.addAction(self.open_action)
        toolbar.addAction(self.save_action)
        toolbar.addAction(self.exit_action)

    def on_text_changed(self):
        length = len(self.text_input.toPlainText())
        self.statusBar().showMessage(f"Length: {length}")
    def open_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open File", "", "Text Files (*.txt);;All Files (*)"
    )
        if not file_path:
            return
        try:
            with open(file_path, "r", encoding="utf-8") as handle:
                self.text_input.setPlainText(handle.read())
            self.current_path = file_path
            self.statusBar().showMessage(f"Opened: {file_path}")
        except OSError as exc:
            QMessageBox.critical(self, "Error", f"Failed to open file: {exc}")

    def save_file(self):
        if not getattr(self, "current_path", None):
            self.statusBar().showMessage("No file path yet (Save As in next step)")
            return
        try:
            with open(self.current_path, "w", encoding="utf-8") as handle:
                handle.write(self.text_input.toPlainText())
            self.statusBar().showMessage(f"Saved: {self.current_path}")
        except OSError as exc:
            QMessageBox.critical(self, "Error", f"Failed to save file: {exc}")


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
