import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QLabel, QPushButton, QWidget, QVBoxLayout, QStatusBar)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PlakOn - License Plate Recognition")
        self.setFixedSize(800,500)
        self.setStyleSheet("""
            background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1
                    stop:0 #FFFFFF,
                    stop:1 #0033CC
                ); 
        """)
app = QApplication(sys.argv)
window = MainWindow()
window.show()
sys.exit(app.exec())