import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QLabel, QPushButton, QWidget, QVBoxLayout, QStatusBar)
from PyQt6.QtCore import QSize
from PyQt6.QtGui import QIcon

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PlakOn - License Plate Recognition")
        self.setFixedSize(800, 500)
        self.setStyleSheet("""
            QMainWindow {
                background: qlineargradient(
                    x1:0, y1:0, x2:1.5, y2:1.5,
                    stop:0 #FFFFFF,
                    stop:1 #0033CC
                ); 
            }
        """)
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout()
        central_widget.setLayout(layout)
        self.icon_Button = QPushButton('Icon Button')
        try:
            icon = QIcon('maximize_pressed.svg')
            if not icon.isNull():
                self.icon_Button.setIcon(icon)
                self.icon_Button.setIconSize(QSize(20, 20))
            else:
                print("آیکون پیدا نشد!")
        except:
            print("خطا در بارگذاری آیکون")
        
        layout.addWidget(self.icon_Button)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())