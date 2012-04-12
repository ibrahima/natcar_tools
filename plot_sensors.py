__author__ = 'Ibrahim'
import sys

from PyQt4 import QtCore, QtGui
import numpy as np
import pyqtgraph as pg

## create GUI
app = QtGui.QApplication([])
w = QtGui.QMainWindow()
w.resize(800,600)
v = pg.GraphicsView()
#v.invertY(True)  ## Images usually have their Y-axis pointing downward
v.setAspectLocked(True)
v.enableMouse(True)
v.autoPixelScale = False
w.setCentralWidget(v)
s = v.scene()
#v.setRange(QtCore.QRect(-2, -2, 220, 220))
w.show()

pi1 = pg.PlotItem()
r = abs(np.random.normal(loc=0, scale=100*0.1, size=100))
curve = pg.PlotCurveItem()
curve.updateData(r)
pi1.addCurve(curve)
s.addItem(pi1)

pi1.scale(1.0, 1.0)
pi1.setGeometry(10, 10, 400, 300)

pi1.plot()

def updateImage():
    r = abs(np.random.normal(loc=0, scale=100*0.1, size=100))
    curve.updateData(r)

## Rapidly update one of the images with random noise
t = QtCore.QTimer()
t.timeout.connect(updateImage)
t.start(50)

## Start Qt event loop unless running in interactive mode.
if sys.flags.interactive != 1:
    app.exec_()
