import sys
import os
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QLabel, QPushButton, QStackedWidget)
from PyQt6.QtCore import Qt, QTimer, QUrl
from PyQt6.QtMultimedia import QMediaPlayer
from PyQt6.QtMultimediaWidgets import QVideoWidget

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PlakOn")
        self.setFixedSize(200, 300)
        self.setCentralWidget(self.stacked_widget)
        self.video_page = QWidget()
        self.setup_video_page()
        self.main_page = QWidget()
        self.setup_main_page()
        self.stacked_widget.addWidget(self.video_page)
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
            QTimer.singleShot(100, self.go_to_main_page)
    
    def on_video_finished(self, status):
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            print("ویدیو به پایان رسید")
            QTimer.singleShot(500, self.go_to_main_page)
    
    def go_to_main_page(self):
        self.stacked_widget.setCurrentWidget(self.main_page)
        self.setWindowTitle("PlakOn")
    
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
    
    def start_program(self):
        print("برنامه شروع شد!")
        self.show_message("در حال آماده‌سازی...")
    
    def show_message(self, message):
        from PyQt6.QtWidgets import QMessageBox
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