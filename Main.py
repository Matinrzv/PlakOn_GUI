import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                          QLabel, QPushButton, QStackedWidget)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.GUIinit()
    def GUIinit(self):
        button = QPushButton('Click!',self)
        button.clicked.connect(self.button_clicked)
        layout = QVBoxLayout()
        layout.addWidget(button)
        self.setLayout(layout)
        self.setWindowTitle('PlakOn')
        self.setGeometry(300,300,300,300)
    def button_clicked(self):
        print("Clicked...")
if __name__=='__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())