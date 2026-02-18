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
    QTextEdit
)

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

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
