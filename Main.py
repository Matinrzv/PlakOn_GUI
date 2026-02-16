import sys
from PyQt6.QtWidgets import QApplication, QLabel, QMainWindow, QPushButton, QVBoxLayout, QWidget


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PyQt6 Lesson 2 - Signals and Slots")
        self.resize(600, 400)

        self.click_count = 0

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout()
        central_widget.setLayout(layout)

        self.title_label = QLabel("Lesson 2: Button Click Event")
        self.status_label = QLabel("Button has not been clicked yet.")
        self.click_button = QPushButton("Click Me")
        self.click_button_reset = QPushButton("Reset!")

        self.click_button.clicked.connect(self.on_button_clicked)
        self.click_button_reset.clicked.connect(self.on_button_clicked_to_reset)

        layout.addWidget(self.title_label)
        layout.addWidget(self.status_label)
        layout.addWidget(self.click_button)
        layout.addWidget(self.click_button_reset)
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
def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
