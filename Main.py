import sys
import re
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLabel,
    QLineEdit,
    QComboBox,
    QTextEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QMessageBox,
    QHeaderView,
)

from backend.service import PlateRecordService


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.service = PlateRecordService()
        self.selected_record_id: int | None = None
        self.setWindowTitle("PlakOn Panel")
        self.resize(980, 620)
        self._build_ui()
        self.load_records()
        self.statusBar().showMessage("Panel ready")

    def _build_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        page_layout = QVBoxLayout(central_widget)

        title = QLabel("PlakOn Management Panel")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        page_layout.addWidget(title)

        search_row = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by plate number...")
        search_button = QPushButton("Search")
        reset_button = QPushButton("Reset")
        search_button.clicked.connect(self.search_records)
        reset_button.clicked.connect(self.reset_search)
        search_row.addWidget(self.search_input)
        search_row.addWidget(search_button)
        search_row.addWidget(reset_button)
        page_layout.addLayout(search_row)

        form_layout = QFormLayout()
        plate_row_widget = QWidget()
        plate_row = QHBoxLayout(plate_row_widget)
        plate_row.setContentsMargins(0, 0, 0, 0)

        self.plate_first_two_input = QLineEdit()
        self.plate_first_two_input.setPlaceholderText("12")
        self.plate_first_two_input.setMaxLength(2)
        self.plate_first_two_input.setFixedWidth(60)

        self.plate_letter_input = QComboBox()
        self.plate_letter_input.addItems(
            [
                "الف",
                "ب",
                "پ",
                "ت",
                "ث",
                "ج",
                "چ",
                "ح",
                "خ",
                "د",
                "ذ",
                "ر",
                "ز",
                "ژ",
                "س",
                "ش",
                "ص",
                "ض",
                "ط",
                "ظ",
                "ع",
                "غ",
                "ف",
                "ق",
                "ک",
                "گ",
                "ل",
                "م",
                "ن",
                "و",
                "ه",
                "ی",
            ]
        )
        self.plate_letter_input.setFixedWidth(70)

        self.plate_three_digits_input = QLineEdit()
        self.plate_three_digits_input.setPlaceholderText("345")
        self.plate_three_digits_input.setMaxLength(3)
        self.plate_three_digits_input.setFixedWidth(70)

        iran_label = QLabel("ایران")
        iran_label.setStyleSheet("font-weight: bold;")

        self.plate_region_two_input = QLineEdit()
        self.plate_region_two_input.setPlaceholderText("67")
        self.plate_region_two_input.setMaxLength(2)
        self.plate_region_two_input.setFixedWidth(60)

        plate_row.addWidget(self.plate_first_two_input)
        plate_row.addWidget(self.plate_letter_input)
        plate_row.addWidget(self.plate_three_digits_input)
        plate_row.addWidget(iran_label)
        plate_row.addWidget(self.plate_region_two_input)
        plate_row.addStretch(1)

        self.owner_input = QLineEdit()
        self.car_input = QLineEdit()
        self.notes_input = QTextEdit()
        self.notes_input.setMaximumHeight(80)
        form_layout.addRow("Plate Number:", plate_row_widget)
        form_layout.addRow("Owner Name:", self.owner_input)
        form_layout.addRow("Car Model:", self.car_input)
        form_layout.addRow("Notes:", self.notes_input)
        page_layout.addLayout(form_layout)

        button_row = QHBoxLayout()
        add_button = QPushButton("Add")
        update_button = QPushButton("Update")
        delete_button = QPushButton("Delete")
        clear_button = QPushButton("Clear Form")
        add_button.clicked.connect(self.add_record)
        update_button.clicked.connect(self.update_record)
        delete_button.clicked.connect(self.delete_record)
        clear_button.clicked.connect(self.clear_form)
        button_row.addWidget(add_button)
        button_row.addWidget(update_button)
        button_row.addWidget(delete_button)
        button_row.addWidget(clear_button)
        page_layout.addLayout(button_row)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            ["ID", "Plate Number", "Owner Name", "Car Model", "Notes", "Created At"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.itemSelectionChanged.connect(self.on_table_selection_changed)
        page_layout.addWidget(self.table)

    def _normalize_digits(self, value: str) -> str:
        translation_table = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
        return value.translate(translation_table)

    def _read_plate_parts(self) -> tuple[str, str, str, str]:
        first_two = self._normalize_digits(self.plate_first_two_input.text().strip())
        letter = self.plate_letter_input.currentText().strip()
        three_digits = self._normalize_digits(self.plate_three_digits_input.text().strip())
        region_two = self._normalize_digits(self.plate_region_two_input.text().strip())
        return first_two, letter, three_digits, region_two

    def _build_plate_number(self) -> str:
        first_two, letter, three_digits, region_two = self._read_plate_parts()
        return f"{first_two.zfill(2)} {letter} {three_digits.zfill(3)} ایران {region_two.zfill(2)}"

    def _read_form(self):
        return {
            "plate_number": self._build_plate_number(),
            "owner_name": self.owner_input.text().strip(),
            "car_model": self.car_input.text().strip(),
            "notes": self.notes_input.toPlainText().strip(),
        }

    def _validate_form(self) -> bool:
        data = self._read_form()
        first_two, _, three_digits, region_two = self._read_plate_parts()

        if not first_two or not three_digits or not region_two:
            QMessageBox.warning(
                self,
                "Validation Error",
                "لطفا همه بخش‌های پلاک را تکمیل کنید.",
            )
            return False

        if not (first_two.isdigit() and three_digits.isdigit() and region_two.isdigit()):
            QMessageBox.warning(
                self,
                "Validation Error",
                "بخش‌های عددی پلاک باید فقط شامل رقم باشند.",
            )
            return False

        if len(first_two) > 2 or len(three_digits) > 3 or len(region_two) > 2:
            QMessageBox.warning(
                self,
                "Validation Error",
                "فرمت پلاک باید حداکثر ۲ رقم + حرف + ۳ رقم + ایران + ۲ رقم باشد.",
            )
            return False

        if not data["owner_name"] or not data["car_model"]:
            QMessageBox.warning(
                self,
                "Validation Error",
                "Owner name and car model are required.",
            )
            return False
        return True

    def load_records(self, records=None):
        records = records if records is not None else self.service.list_records()
        self.table.setRowCount(len(records))
        for row_index, record in enumerate(records):
            values = [
                str(record["id"]),
                record["plate_number"],
                record["owner_name"],
                record["car_model"],
                record["notes"],
                record["created_at"],
            ]
            for col_index, value in enumerate(values):
                self.table.setItem(row_index, col_index, QTableWidgetItem(value))
        self.statusBar().showMessage(f"{len(records)} record(s) loaded")

    def search_records(self):
        query = self.search_input.text().strip()
        if not query:
            self.load_records()
            return
        self.load_records(self.service.search_by_plate(query))

    def reset_search(self):
        self.search_input.clear()
        self.load_records()

    def add_record(self):
        if not self._validate_form():
            return
        data = self._read_form()
        self.service.add_record(
            data["plate_number"],
            data["owner_name"],
            data["car_model"],
            data["notes"],
        )
        self.clear_form()
        self.load_records()

    def update_record(self):
        if self.selected_record_id is None:
            QMessageBox.information(self, "No Selection", "Please select a row to update.")
            return
        if not self._validate_form():
            return
        data = self._read_form()
        updated = self.service.update_record(
            self.selected_record_id,
            data["plate_number"],
            data["owner_name"],
            data["car_model"],
            data["notes"],
        )
        if updated:
            self.load_records()
            self.statusBar().showMessage(f"Record {self.selected_record_id} updated")
        else:
            QMessageBox.warning(self, "Error", "Selected record was not found.")

    def delete_record(self):
        if self.selected_record_id is None:
            QMessageBox.information(self, "No Selection", "Please select a row to delete.")
            return
        confirm = QMessageBox.question(
            self,
            "Delete Record",
            f"Delete record #{self.selected_record_id}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        deleted = self.service.delete_record(self.selected_record_id)
        if deleted:
            self.clear_form()
            self.load_records()
        else:
            QMessageBox.warning(self, "Error", "Selected record was not found.")

    def on_table_selection_changed(self):
        selected_items = self.table.selectedItems()
        if not selected_items:
            return
        row = selected_items[0].row()
        self.selected_record_id = int(self.table.item(row, 0).text())
        plate_text = self.table.item(row, 1).text()
        self._fill_plate_fields(plate_text)
        self.owner_input.setText(self.table.item(row, 2).text())
        self.car_input.setText(self.table.item(row, 3).text())
        self.notes_input.setPlainText(self.table.item(row, 4).text())

    def _fill_plate_fields(self, plate_text: str):
        pattern = r"^\s*(\d{2})\s+(\S+)\s+(\d{3})\s+ایران\s+(\d{2})\s*$"
        match = re.match(pattern, plate_text)
        if not match:
            self.plate_first_two_input.clear()
            self.plate_three_digits_input.clear()
            self.plate_region_two_input.clear()
            return

        first_two, letter, three_digits, region_two = match.groups()
        self.plate_first_two_input.setText(first_two)
        self.plate_three_digits_input.setText(three_digits)
        self.plate_region_two_input.setText(region_two)

        index = self.plate_letter_input.findText(letter)
        if index >= 0:
            self.plate_letter_input.setCurrentIndex(index)

    def clear_form(self):
        self.selected_record_id = None
        self.plate_first_two_input.clear()
        self.plate_three_digits_input.clear()
        self.plate_region_two_input.clear()
        self.plate_letter_input.setCurrentIndex(0)
        self.owner_input.clear()
        self.car_input.clear()
        self.notes_input.clear()
        self.table.clearSelection()
        self.statusBar().showMessage("Form cleared")


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
