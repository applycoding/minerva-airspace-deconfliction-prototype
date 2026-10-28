from PySide6.QtWidgets import QMainWindow, QLabel


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('MINERVA — simulation only')
        self.resize(960, 640)
        self.setCentralWidget(QLabel('MINERVA\nSimulation only; never flown.\nDesktop shell — planning panels are not yet implemented.'))
