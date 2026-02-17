import sys
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QVBoxLayout,
    QWidget,
)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Lesson 4 Test App")
        self.resize(700, 420)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        self.page_layout = QVBoxLayout()
        central_widget.setLayout(self.page_layout)

        # TODO 1:
        # A form using QGridLayout with these fields:
        # - Name (QLineEdit)
        # - Age (QLineEdit, valid range: 1-120)
        # - City (QComboBox with at least 4 cities)
        # - Job (QLineEdit)

        # TODO 2:
        # A button row using QHBoxLayout with:
        # - Save button
        # - Clear button

        # TODO 3:
        # A result QLabel below buttons.

        # TODO 4:
        # Connect signals:
        # - Save clicked -> save_profile
        # - Clear clicked -> clear_form
        # - textChanged for inputs -> update_save_state

        # TODO 5:
        # Implement validation:
        # - Name not empty
        # - Age must be integer in [1, 120]
        # - Job not empty

    def is_valid_age(self, age_text: str) -> bool:
        # TODO: Implement age validation
        return False

    def update_save_state(self):
        # TODO: Enable save button only when all inputs are valid
        pass

    def save_profile(self):
        # TODO: Show final summary in result label
        # Example: Saved: Ali, 22, Tehran, Developer
        pass

    def clear_form(self):
        # TODO: Clear all fields and reset result label
        pass


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
