import sys
from PyQt6.QtWidgets import (
    QApplication,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PyQt6 Lesson 3 - QLineEdit")
        self.resize(600, 400)

        self.click_count = 0

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout()
        central_widget.setLayout(layout)

        self.title_label = QLabel("Lesson 3: QLineEdit and Input Validation")
        self.status_label = QLabel("Button has not been clicked yet.")
        self.click_button = QPushButton("Click Me")
        self.click_button_reset = QPushButton("Reset!")
        self.input_label = QLabel("Enter your name:")
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Type your name and press Enter")
        self.name_input.setMaxLength(30)
        self.submit_button = QPushButton("Submit Name")
        self.name_result_label = QLabel("No name submitted yet.")

        self.click_button.clicked.connect(self.on_button_clicked)
        self.click_button_reset.clicked.connect(self.on_button_clicked_to_reset)
        self.name_input.textChanged.connect(self.on_name_text_changed)
        self.name_input.returnPressed.connect(self.submit_name)
        self.submit_button.clicked.connect(self.submit_name)

        layout.addWidget(self.title_label)
        layout.addWidget(self.status_label)
        layout.addWidget(self.click_button)
        layout.addWidget(self.click_button_reset)
        layout.addSpacing(20)
        layout.addWidget(self.input_label)
        layout.addWidget(self.name_input)
        layout.addWidget(self.submit_button)
        layout.addWidget(self.name_result_label)

    def on_button_clicked(self):
        self.click_count += 1
        self.setWindowTitle(f"Clicks: {self.click_count}")
        self.status_label.setText(f"Clicked {self.click_count} time(s).")
        if self.click_count == 10:
            self.status_label.setText("Great! 10 clicks reached.")

    def on_button_clicked_to_reset(self):
        self.click_count = 0
        self.setWindowTitle("Clicks: 0")
        self.status_label.setText(f"Clicked {self.click_count} time(s).")

    def on_name_text_changed(self, text):
        cleaned_text = text.strip()
        if cleaned_text:
            self.name_result_label.setText(f"Typing: {cleaned_text}")
        else:
            self.name_result_label.setText("No name submitted yet.")

    def submit_name(self):
        user_name = self.name_input.text().strip()
        if not user_name:
            self.name_result_label.setText("Please enter a valid name.")
            return
        self.name_result_label.setText(f"Hello, {user_name}!")
        self.name_input.clear()


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
