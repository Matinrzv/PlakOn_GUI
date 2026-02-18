import sys
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QMainWindow,
    QMessageBox,
    QTextEdit,
)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PyQt6 Lesson 5 - Menus and Toolbar")
        self.resize(800, 500)

        self.editor = QTextEdit()
        self.setCentralWidget(self.editor)

        self.current_path = None

        self._build_actions()
        self._build_menus()
        self._build_toolbar()
        self.statusBar().showMessage("Ready")

        self.editor.textChanged.connect(self.on_text_changed)

    def _build_actions(self):
        self.new_action = QAction("New", self)
        self.new_action.setShortcut("Ctrl+N")
        self.new_action.triggered.connect(self.new_file)

        self.open_action = QAction("Open...", self)
        self.open_action.setShortcut("Ctrl+O")
        self.open_action.triggered.connect(self.open_file)

        self.save_action = QAction("Save", self)
        self.save_action.setShortcut("Ctrl+S")
        self.save_action.triggered.connect(self.save_file)

        self.save_as_action = QAction("Save As...", self)
        self.save_as_action.setShortcut("Ctrl+Shift+S")
        self.save_as_action.triggered.connect(self.save_file_as)

        self.exit_action = QAction("Exit", self)
        self.exit_action.setShortcut("Ctrl+Q")
        self.exit_action.triggered.connect(self.close)

    def _build_menus(self):
        file_menu = self.menuBar().addMenu("File")
        file_menu.addAction(self.new_action)
        file_menu.addAction(self.open_action)
        file_menu.addAction(self.save_action)
        file_menu.addAction(self.save_as_action)
        file_menu.addSeparator()
        file_menu.addAction(self.exit_action)

    def _build_toolbar(self):
        toolbar = self.addToolBar("Main")
        toolbar.addAction(self.new_action)
        toolbar.addAction(self.open_action)
        toolbar.addAction(self.save_action)

    def on_text_changed(self):
        length = len(self.editor.toPlainText())
        self.statusBar().showMessage(f"Length: {length}")

    def new_file(self):
        if not self._confirm_discard_changes():
            return
        self.editor.clear()
        self.current_path = None
        self.statusBar().showMessage("New file")

    def open_file(self):
        if not self._confirm_discard_changes():
            return
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open File",
            "",
            "Text Files (*.txt);;All Files (*)",
        )
        if not file_path:
            return
        try:
            with open(file_path, "r", encoding="utf-8") as handle:
                self.editor.setPlainText(handle.read())
            self.current_path = file_path
            self.statusBar().showMessage(f"Opened: {file_path}")
        except OSError as exc:
            QMessageBox.critical(self, "Error", f"Failed to open file: {exc}")

    def save_file(self):
        if not self.current_path:
            self.save_file_as()
            return
        try:
            with open(self.current_path, "w", encoding="utf-8") as handle:
                handle.write(self.editor.toPlainText())
            self.statusBar().showMessage(f"Saved: {self.current_path}")
        except OSError as exc:
            QMessageBox.critical(self, "Error", f"Failed to save file: {exc}")

    def save_file_as(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save File As",
            "",
            "Text Files (*.txt);;All Files (*)",
        )
        if not file_path:
            return
        self.current_path = file_path
        self.save_file()

    def _confirm_discard_changes(self):
        if not self.editor.document().isModified():
            return True
        reply = QMessageBox.question(
            self,
            "Unsaved Changes",
            "You have unsaved changes. Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        return reply == QMessageBox.StandardButton.Yes


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
