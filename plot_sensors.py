__author__ = 'Ibrahim'
import sys

from PyQt4 import QtCore, QtGui
import numpy as np
import pyqtgraph as pg
import array
import argparse
import random

class TimeSeriesPlotter():
    def __init__(self, historySize=100):
        self.data = {}
        self.indices = {}
        self.curves = {}
        self.historySize = historySize
        self.app = QtGui.QApplication([])
        self.w = QtGui.QMainWindow()
        self.w.resize(800,600)
        self.v = pg.GraphicsView()
        #v.invertY(True)  ## Images usually have their Y-axis pointing downward
        self.v.setAspectLocked(True)
        self.v.enableMouse(True)
        self.v.autoPixelScale = False
        self.w.setCentralWidget(self.v)
        self.s = self.v.scene()
        #v.setRange(QtCore.QRect(-2, -2, 220, 220))
        self.w.show()
        self.pi = pg.PlotItem()
        self.s.addItem(self.pi)
        self.pi.scale(1.0, 1.0)
        self.pi.setGeometry(10, 10, 400, 300)

    def addData(self, value, key=0):
        if self.data.has_key(key):
            idx = self.indices[key]
            self.data[key][idx] = value
            self.indices[key] = (idx + 1) % self.historySize # Ring buffering
        else:
            self.data[key] = np.zeros(self.historySize)
            self.data[key][0] = value
            self.indices[key] = 1
            curve = pg.PlotCurveItem()
            self.curves[key] = curve
            self.pi.addCurve(curve)
        self.curves[key].updateData(self.data[key])

    def addRandomData(self, key=0):
        r = random.random()
        self.addData(r, key)

tsp = TimeSeriesPlotter()
## Rapidly update one of the images with random noise
t = QtCore.QTimer()
t.timeout.connect(tsp.addRandomData)
t.start(50)

## Start Qt event loop unless running in interactive mode.
if sys.flags.interactive != 1:
    tsp.app.exec_()
