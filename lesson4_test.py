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
    QGridLayout
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

        title = QLabel("Lesson 4 Test App")
        self.page_layout.addWidget(title)

        form_layout = QGridLayout()
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Full name")

        self.age_input = QLineEdit()
        self.age_input.setPlaceholderText("Age (1-120)")
        self.age_input.setMaxLength(3)

        self.city_box = QComboBox()
        self.city_box.addItems(["Tehran","Shiraz", "Tabriz", "Mashhad", "Isfahan", "Ahvaz"])

        self.job_input = QLineEdit()
        self.job_input.setPlaceholderText("Job title")

        form_layout.addWidget(QLabel("Name:"), 0, 0)
        form_layout.addWidget(self.name_input, 0, 1)
        form_layout.addWidget(QLabel("Age:"), 1, 0)
        form_layout.addWidget(self.age_input, 1, 1)
        form_layout.addWidget(QLabel("City:"), 2, 0)
        form_layout.addWidget(self.city_box, 2, 1)
        form_layout.addWidget(QLabel("Job:"), 3, 0)
        form_layout.addWidget(self.job_input, 3, 1)
        self.page_layout.addLayout(form_layout)   

        button_layout = QHBoxLayout()
        self.save_button = QPushButton("Save")
        self.clear_button = QPushButton("Clear")
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.clear_button)
        self.page_layout.addLayout(button_layout)

        self.result_label = QLabel("No profile submitted yet.")
        self.page_layout.addWidget(self.result_label)

        self.save_button.clicked.connect(self.save_profile)
        self.clear_button.clicked.connect(self.clear_form)
        self.name_input.textChanged.connect(self.update_save_state)
        self.age_input.textChanged.connect(self.update_save_state)
        self.job_input.textChanged.connect(self.update_save_state)
        self.update_save_state()   

    def is_valid_age(self, age_text):
        return age_text.isdigit() and 1 <= int(age_text) <= 120

    def update_save_state(self):
        has_name = bool(self.name_input.text().strip())
        has_job = bool(self.job_input.text().strip())
        valid_age = self.is_valid_age(self.age_input.text().strip())
        self.save_button.setEnabled(has_name and has_job and valid_age)

    def save_profile(self):
        name = self.name_input.text().strip()
        age = self.age_input.text().strip()
        city = self.city_box.currentText()
        job = self.job_input.text().strip()

        if not name:
            self.result_label.setText("Please enter a valid name.")
            return
        if not self.is_valid_age(age):
            self.result_label.setText("Please enter a valid age (1-120).")
            return
        if not job:
            self.result_label.setText("Please enter a valid job title.")
            return

        self.result_label.setText(f"Saved: {name}, {age}, {city}, {job}")
      
    def clear_form(self):
        self.name_input.clear()
        self.age_input.clear()
        self.job_input.clear()
        self.city_box.setCurrentIndex(0)
        self.result_label.setText("No profile submitted yet.")


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
