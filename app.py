import time
import Queue
from rpiMonitor import *
from livedatafeed import LiveDataFeed

import sys
import random
import matplotlib
matplotlib.use("Qt5Agg")
from PyQt5 import QtCore
from PyQt5.QtWidgets import QApplication, QMainWindow, QMenu, QVBoxLayout, QSizePolicy, QMessageBox, QWidget
from numpy import arange, sin, pi
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

class MyMplCanvas(FigureCanvas):
    """Ultimately, this is a QWidget (as well as a FigureCanvasAgg, etc.)."""
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = fig.add_subplot(111)
        # We want the axes cleared every time plot() is called
        #self.axes.hold(False)

        self.compute_initial_figure()
        FigureCanvas.__init__(self, fig)
        self.setParent(parent)

        FigureCanvas.setSizePolicy(self,
                                   QSizePolicy.Expanding,
                                   QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)

    def compute_initial_figure(self):
        pass

class MyDynamicMplCanvas(MyMplCanvas):
    """A canvas that updates itself every second with a new plot."""
    def __init__(self, *args, **kwargs):
        MyMplCanvas.__init__(self, *args, **kwargs)
        timer = QtCore.QTimer(self)
        timer.timeout.connect(self.on_timer)
        timer.start(1000)
        self.livefeed = LiveDataFeed()
        self.xydata = []

    def on_start(self):
        channel_A =  0x30
        channel_B =  0x34
        StartGPIO()
        print("GPIO setup complete")

        StartSPI()
        print("SPI setup complete")
        
        self.data_q = Queue.Queue()
        self.adc = ADCMonitor(self.data_q,0)
        self.dac = DAC()
        self.dac.write(0.75000,channel_B)
        self.adc.start()

    def on_stop(self):
        self.adc.join()
        

    def on_timer(self):
        self.read_adc_data()
        self.update_figure()

    def read_adc_data(self):
        qdata = list(get_all_from_queue(self.data_q))
        if len(qdata)>0:
            data = dict(ts = qdata[-1][0],
                        voltage = qdata[-1][1]
                        )
            self.livefeed.add_data(data)
        
    def compute_initial_figureself):
        self.axes.plot([0], [0], 'r')

    def update_figure(self):

        data = self.livefeed.read_data()
        self.xydata.append((data['ts'],data['voltage']))

        xdata = [s[0] for s in self.xydata]
        ydata = [s[1] for s in self.xydata]
        
        # Build a list of 4 random integers between 0 and 10 (both inclusive)
        #l = [random.randint(0, 10) for i in range(4)]

        self.axes.plot(xdata, ydata, 'r')
        self.draw()

class ApplicationWindow(QMainWindow):
    def __init__(self):
        
        QMainWindow.__init__(self)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setWindowTitle("application main window")

        self.file_menu = QMenu('&File', self)
        self.file_menu.addAction('&Quit', self.fileQuit,
                                 QtCore.Qt.CTRL + QtCore.Qt.Key_Q)
        self.menuBar().addMenu(self.file_menu)

        self.help_menu = QMenu('&Help', self)
        self.menuBar().addSeparator()
        self.menuBar().addMenu(self.help_menu)

        self.help_menu.addAction('&About', self.about)

        self.main_widget = QWidget(self)

        self.l = QVBoxLayout(self.main_widget)
        self.dc = MyDynamicMplCanvas(self.main_widget, width=5, height=4, dpi=100)
        self.l.addWidget(self.dc)

        self.main_widget.setFocus()
        self.setCentralWidget(self.main_widget)

        self.statusBar().showMessage("All hail matplotlib!", 2000)

    def start(self):
        self.dc.on_start()
        #time.sleep(20)
        #self.dc.on_stop()

    def fileQuit(self):
        self.close()

    def closeEvent(self, ce):
        self.fileQuit()

    def about(self):
        QMessageBox.about(self, "About",
"""embedding_in_qt5.py example
"""
)

def get_all_from_queue(Q):
    """ Generator to yield one after the others all items 
        currently in the queue Q, without any waiting.
    """
    try:
        while True:
            yield Q.get_nowait( )
    except Queue.Empty:
        raise StopIteration

def get_item_from_queue(Q, timeout=0.01):

    """ Attempts to retrieve an item from the queue Q. If Q is
        empty, None is returned.
        
        Blocks for 'timeout' seconds in case the queue is empty,
        so don't use this method for speedy retrieval of multiple
        items (use get_all_from_queue for that).
    """
    try:
        item = Q.get(True, timeout)
    except Queue.Empty: 
        return None
    
    return item

    

if __name__ == '__main__':
    app = QApplication(sys.argv)

    aw = ApplicationWindow()
    aw.setWindowTitle("PyQt5 Matplot Example")
    aw.show()
    aw.start()

    #sys.exit(qApp.exec_())
    app.exec_()

    
#DAC address

'''
channel_A =  0x30
channel_B =  0x34
StartGPIO()
print("GPIO setup complete")

StartSPI()
print("SPI setup complete")
data_q = Queue.Queue()
adc = ADCMonitor(data_q,0)
dac = DAC()
dac.write(0.75000,channel_B)
adc.start()

time.sleep(10)
adc.join()
'''
