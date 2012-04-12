__author__ = 'Ibrahim'
import sys

from PyQt4 import QtCore, QtGui
import numpy as np
import pyqtgraph as pg
import array
import argparse
import random

class TimeSeriesPlotter():
    """
    A class for plotting data over time. Uses a clever trick found on Stack Overflow and stores the data twice so that
    it can easily get a view of the data by slicing, and uses the excellent PyQtGraph library by Luke Campagnola.
    """
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
        self.pi.scale(0.7, 0.7)
        self.pi.setGeometry(10, 10, 800, 600)
        self.lastval = 10

    def addData(self, value, key=0):
        if not self.data.has_key(key):
            self.data[key] = np.zeros(self.historySize*2)
            self.indices[key] = 0
            self.curves[key] = pg.PlotCurveItem()
            self.pi.addCurve(self.curves[key])
        idx = self.indices[key]
        self.data[key][idx] = value
        self.data[key][idx + self.historySize] = value
        self.curves[key].updateData(self.data[key][idx+1 : idx+self.historySize]+1)
        self.indices[key] = (idx + 1) % self.historySize # Ring buffering

    def addRandomData(self, key=0):
        r = random.gauss(self.lastval, 1)
        self.addData(r, key)
        self.lastval = r

tsp = TimeSeriesPlotter(50)
## Rapidly update one of the images with random noise
t = QtCore.QTimer()
t.timeout.connect(tsp.addRandomData)
t.start(50)

## Start Qt event loop unless running in interactive mode.
if sys.flags.interactive != 1:
    tsp.app.exec_()
