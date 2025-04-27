import sys
import cProfile

from PyQt5.QtCore import QCoreApplication
from PyQt5.QtWidgets import *

from main_window import MainWindow

if __name__ == "__main__":
    profiler = cProfile.Profile()
    profiler.enable()

    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()


    def close_app():
        profiler.disable()
        profiler.dump_stats('profile_data.prof')
        print("profile_data.prof saved.")


    QCoreApplication.instance().aboutToQuit.connect(close_app)
    sys.exit(app.exec())