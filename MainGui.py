import sys
import os
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QStackedWidget,
    QLineEdit,
    QComboBox,
    QFormLayout,
    QMessageBox,
    QHBoxLayout,
)
from PyQt6.QtCore import Qt, QTimer, QUrl
from PyQt6.QtMultimedia import QMediaPlayer
from PyQt6.QtMultimediaWidgets import QVideoWidget


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PlakOn")
        self.setFixedSize(420, 520)
        self.stacked_widget = QStackedWidget()
        self.users = {}

        self.setCentralWidget(self.stacked_widget)

        self.video_page = QWidget()
        self.auth_page = QWidget()
        self.setup_video_page()
        self.setup_auth_page()
        self.main_page = QWidget()
        self.setup_main_page()

        self.stacked_widget.addWidget(self.video_page)
        self.stacked_widget.addWidget(self.auth_page)
        self.stacked_widget.addWidget(self.main_page)
        self.stacked_widget.setCurrentWidget(self.video_page)

        self.setStyleSheet("""
            QMainWindow {
                background-color: black;
            }
        """)

    def setup_video_page(self):
        layout = QVBoxLayout()
        self.video_page.setLayout(layout)
        layout.setContentsMargins(0, 0, 0, 0)

        self.video_widget = QVideoWidget()
        self.video_widget.setStyleSheet("background-color: black;")
        layout.addWidget(self.video_widget)

        self.player = QMediaPlayer()
        self.player.setVideoOutput(self.video_widget)

        video_path = "grok-video-dc701094-adfa-49fc-9dc0-a3135b8a6c79.mp4"
        if os.path.exists(video_path):
            self.player.setSource(QUrl.fromLocalFile(os.path.abspath(video_path)))
            self.player.play()
            print(f"در حال پخش ویدیو: {video_path}")
            self.player.mediaStatusChanged.connect(self.on_video_finished)
        else:
            print(f"خطا: فایل ویدیو پیدا نشد!")
            QTimer.singleShot(100, self.go_to_auth_page)

    def on_video_finished(self, status):
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            print("ویدیو به پایان رسید")
            QTimer.singleShot(500, self.go_to_auth_page)

    def go_to_auth_page(self):
        self.stacked_widget.setCurrentWidget(self.auth_page)
        self.setWindowTitle("PlakOn | ورود / ثبت نام")

    def go_to_main_page(self):
        self.stacked_widget.setCurrentWidget(self.main_page)
        self.setWindowTitle("PlakOn")

    def setup_auth_page(self):
        layout = QVBoxLayout()
        self.auth_page.setLayout(layout)
        layout.setContentsMargins(22, 22, 22, 22)
        layout.setSpacing(10)

        title = QLabel("ورود / ثبت نام")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #123566;")
        subtitle = QLabel("نوع حساب را انتخاب کنید: شخص یا شرکت")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("font-size: 12px; color: #405066;")

        self.account_type = QComboBox()
        self.account_type.addItems(["شخص", "شرکت"])

        form = QFormLayout()
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("نام شخص یا نام شرکت")
        self.identifier_input = QLineEdit()
        self.identifier_input.setPlaceholderText("کد ملی / شناسه ملی")
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("نام کاربری")
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("رمز عبور")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("نوع حساب:", self.account_type)
        form.addRow("نام:", self.name_input)
        form.addRow("شناسه:", self.identifier_input)
        form.addRow("نام کاربری:", self.username_input)
        form.addRow("رمز عبور:", self.password_input)

        btn_row = QHBoxLayout()
        register_btn = QPushButton("ثبت نام")
        login_btn = QPushButton("ورود")
        register_btn.clicked.connect(self.register_user)
        login_btn.clicked.connect(self.login_user)
        btn_row.addWidget(register_btn)
        btn_row.addWidget(login_btn)

        layout.addStretch(1)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(8)
        layout.addLayout(form)
        layout.addLayout(btn_row)
        layout.addStretch(2)

        self.auth_page.setStyleSheet("""
            QWidget {
                background: qlineargradient(
                    x1:0, y1:0, x2:1.2, y2:1.2,
                    stop:0 #F7FBFF,
                    stop:1 #DDEBFA
                );
            }
            QLineEdit, QComboBox {
                background-color: white;
                border: 1px solid #AFC4DA;
                border-radius: 6px;
                padding: 6px;
            }
            QPushButton {
                background-color: #1E78D7;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 7px 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1764B3;
            }
        """)

    def setup_main_page(self):
        layout = QVBoxLayout()
        self.main_page.setLayout(layout)
        layout.setContentsMargins(10, 15, 10, 15)
        title_label = QLabel("PlakOn")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("""
            font-size: 28px;
            font-weight: bold;
            color: #0033CC;
            margin-top: 20px;
            margin-bottom: 5px;
        """)
        subtitle_label = QLabel("تشخیص پلاک")
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle_label.setStyleSheet("""
            font-size: 14px;
            color: #666666;
            margin-bottom: 15px;
            font-weight: normal;
        """)
        start_button = QPushButton("شروع")
        start_button.setFixedSize(120, 35)
        start_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 5px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        start_button.clicked.connect(self.start_program)
        layout.addStretch(1)
        layout.addWidget(title_label)
        layout.addWidget(subtitle_label)
        layout.addSpacing(10)
        layout.addWidget(start_button, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addStretch(2)
        self.main_page.setStyleSheet("""
            QWidget {
                background: qlineargradient(
                    x1:0, y1:0, x2:1.5, y2:1.5,
                    stop:0 #FFFFFF,
                    stop:1 #E6F0FF
                );
            }
        """)
    
    def register_user(self):
        account_type = self.account_type.currentText().strip()
        name = self.name_input.text().strip()
        identifier = self.identifier_input.text().strip()
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()

        if not all([name, identifier, username, password]):
            self.show_message("لطفا تمام فیلدها را تکمیل کنید.")
            return

        key = (account_type, username)
        if key in self.users:
            self.show_message("این نام کاربری قبلا ثبت شده است.")
            return

        self.users[key] = {
            "name": name,
            "identifier": identifier,
            "password": password,
        }
        self.show_message("ثبت نام با موفقیت انجام شد. حالا وارد شوید.")

    def login_user(self):
        account_type = self.account_type.currentText().strip()
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()
        key = (account_type, username)
        user = self.users.get(key)
        if not user or user["password"] != password:
            self.show_message("اطلاعات ورود اشتباه است.")
            return

        self.go_to_main_page()
        self.statusBar().showMessage(f"{account_type} وارد شد: {user['name']}")

    def start_program(self):
        print("برنامه شروع شد!")
        self.show_message("در حال آماده‌سازی...")

    def show_message(self, message):
        msg = QMessageBox(self)
        msg.setWindowTitle("PlakOn")
        msg.setText(message)
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.exec()

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
