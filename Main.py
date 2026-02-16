import sys
from PyQt6.QtWidgets import QApplication,QWidget

app = QApplication(sys.argv)
window = QWidget()
window.setWindowTitle("first app with PyQt6")
window.resize(500,500)
window.show()
sys.exit(app.exec())