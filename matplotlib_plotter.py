#!/usr/bin/env python
import math
"""
This demo demonstrates how to draw a dynamic mpl (matplotlib) 
plot in a wxPython application.

It allows "live" plotting as well as manual zooming to specific
regions.

Both X and Y axes allow "auto" or "manual" settings. For Y, auto
mode sets the scaling of the graph to see all the data points.
For X, auto mode makes the graph "follow" the data. Set it X min
to manual 0 to always see the whole data from the beginning.

Note: press Enter in the 'manual' text box to make a new value 
affect the plot.

Eli Bendersky (eliben@gmail.com)
With modifications by Ibrahim Awwal (ibrahima on github)
License: this code is in the public domain
"""
import os
import pprint
import random
import sys
import wx
import serial
from datetime import datetime # Yeah, screw you too Python
import argparse

# The recommended way to use wx with mpl is with the WXAgg
# backend. 
#
import matplotlib
matplotlib.use('WXAgg')
from matplotlib.figure import Figure
from matplotlib.backends.backend_wxagg import \
    FigureCanvasWxAgg as FigCanvas, \
    NavigationToolbar2WxAgg as NavigationToolbar
import numpy as np
import pylab
from matplotlib.pyplot import legend

class DataGen(object):
    """ A silly class that generates pseudo-random data for
        display in the plot.
    """
    def __init__(self, init=50):
        self.data = self.init = init
        
    def next(self):
        self._recalc_data()
        return self.data
    
    def _recalc_data(self):
        delta = random.uniform(-0.5, 0.5)
        r = random.random()

        if r > 0.9:
            self.data += delta * 15
        elif r > 0.8: 
            # attraction to the initial value
            delta += (0.5 if self.init > self.data else -0.5)
            self.data += delta
        else:
            self.data += delta


class BoundControlBox(wx.Panel):
    """ A static box with a couple of radio buttons and a text
        box. Allows to switch between an automatic mode and a 
        manual mode with an associated value.
    """
    def __init__(self, parent, ID, label, initval):
        wx.Panel.__init__(self, parent, ID)
        
        self.value = initval
        
        box = wx.StaticBox(self, -1, label)
        sizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        
        self.radio_auto = wx.RadioButton(self, -1, 
            label="Auto", style=wx.RB_GROUP)
        self.radio_manual = wx.RadioButton(self, -1,
            label="Manual")
        self.manual_text = wx.TextCtrl(self, -1, 
            size=(35,-1),
            value=str(initval),
            style=wx.TE_PROCESS_ENTER)
        
        self.Bind(wx.EVT_UPDATE_UI, self.on_update_manual_text, self.manual_text)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_text_enter, self.manual_text)
        
        manual_box = wx.BoxSizer(wx.HORIZONTAL)
        manual_box.Add(self.radio_manual, flag=wx.ALIGN_CENTER_VERTICAL)
        manual_box.Add(self.manual_text, flag=wx.ALIGN_CENTER_VERTICAL)
        
        sizer.Add(self.radio_auto, 0, wx.ALL, 10)
        sizer.Add(manual_box, 0, wx.ALL, 10)
        
        self.SetSizer(sizer)
        sizer.Fit(self)
    
    def on_update_manual_text(self, event):
        self.manual_text.Enable(self.radio_manual.GetValue())
    
    def on_text_enter(self, event):
        self.value = self.manual_text.GetValue()
    
    def is_auto(self):
        return self.radio_auto.GetValue()
        
    def manual_value(self):
        return self.value


class GraphFrame(wx.Frame):
    """ The main frame of the application
    """
    title = 'Demo: dynamic matplotlib graph'
    
    def __init__(self):
        wx.Frame.__init__(self, None, -1, self.title)
        
        self.paused = False
        
        self.create_menu()
        self.create_status_bar()
        self.create_main_panel()
        
        self.datagen = DataGen()
        
        self.redraw_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.on_redraw_timer, self.redraw_timer)

        self.redraw_timer.Start(100)
        
        self.timer_callbacks = []
        self.Bind(wx.EVT_CLOSE, self.on_exit)

    def create_menu(self):
        self.menubar = wx.MenuBar()
        
        menu_file = wx.Menu()
        m_expt = menu_file.Append(-1, "&Save plot\tCtrl-S", "Save plot to file")
        self.Bind(wx.EVT_MENU, self.on_save_plot, m_expt)
        menu_file.AppendSeparator()
        m_exit = menu_file.Append(-1, "E&xit\tCtrl-X", "Exit")
        self.Bind(wx.EVT_MENU, self.on_exit, m_exit)
                
        self.menubar.Append(menu_file, "&File")
        self.SetMenuBar(self.menubar)

    def create_main_panel(self):
        self.panel = wx.Panel(self)

        self.init_plot()
        self.canvas = FigCanvas(self.panel, -1, self.fig)

        self.xmin_control = BoundControlBox(self.panel, -1, "X min", 0)
        self.xmax_control = BoundControlBox(self.panel, -1, "X max", 50)
        self.ymin_control = BoundControlBox(self.panel, -1, "Y min", 0)
        self.ymax_control = BoundControlBox(self.panel, -1, "Y max", 100)
        
        self.pause_button = wx.Button(self.panel, -1, "Pause")
        self.Bind(wx.EVT_BUTTON, self.on_pause_button, self.pause_button)
        self.Bind(wx.EVT_UPDATE_UI, self.on_update_pause_button, self.pause_button)
        
        self.cb_grid = wx.CheckBox(self.panel, -1, 
            "Show Grid",
            style=wx.ALIGN_RIGHT)
        self.Bind(wx.EVT_CHECKBOX, self.on_cb_grid, self.cb_grid)
        self.cb_grid.SetValue(True)
        
        self.cb_xlab = wx.CheckBox(self.panel, -1, 
            "Show X labels",
            style=wx.ALIGN_RIGHT)
        self.Bind(wx.EVT_CHECKBOX, self.on_cb_xlab, self.cb_xlab)        
        self.cb_xlab.SetValue(True)
        
        self.hbox1 = wx.BoxSizer(wx.HORIZONTAL)
        self.hbox1.Add(self.pause_button, border=5, flag=wx.ALL | wx.ALIGN_CENTER_VERTICAL)
        self.hbox1.AddSpacer(20)
        self.hbox1.Add(self.cb_grid, border=5, flag=wx.ALL | wx.ALIGN_CENTER_VERTICAL)
        self.hbox1.AddSpacer(10)
        self.hbox1.Add(self.cb_xlab, border=5, flag=wx.ALL | wx.ALIGN_CENTER_VERTICAL)
        
        self.hbox2 = wx.BoxSizer(wx.HORIZONTAL)
        self.hbox2.Add(self.xmin_control, border=5, flag=wx.ALL)
        self.hbox2.Add(self.xmax_control, border=5, flag=wx.ALL)
        self.hbox2.AddSpacer(24)
        self.hbox2.Add(self.ymin_control, border=5, flag=wx.ALL)
        self.hbox2.Add(self.ymax_control, border=5, flag=wx.ALL)
        
        self.vbox = wx.BoxSizer(wx.VERTICAL)
        self.vbox.Add(self.canvas, 1, flag=wx.LEFT | wx.TOP | wx.GROW)        
        self.vbox.Add(self.hbox1, 0, flag=wx.ALIGN_LEFT | wx.TOP)
        self.vbox.Add(self.hbox2, 0, flag=wx.ALIGN_LEFT | wx.TOP)
        
        self.panel.SetSizer(self.vbox)
        self.vbox.Fit(self)
    
    def create_status_bar(self):
        self.statusbar = self.CreateStatusBar()

    def init_plot(self):
        self.dpi = 100
        self.fig = Figure((3.0, 3.0), dpi=self.dpi)

        self.axes = self.fig.add_subplot(111)
        self.axes.set_axis_bgcolor('black')
        self.axes.set_title('Very important random data', size=12)
        
        pylab.setp(self.axes.get_xticklabels(), fontsize=8)
        pylab.setp(self.axes.get_yticklabels(), fontsize=8)

        # plot the data as a line series, and save the reference 
        # to the plotted line series
        #
        self.plots = {}
        self.data = {}
        
    def plot_value(self, key, value, r=-1, g=-1, b=-1):
        """
        Adds a value to the plot with th specified key. Color is only used if
        the line didn't exist before.
        """
        if not self.data.has_key(key):
            self.data[key] = [value]
            r = random.uniform(50,255) if r == -1 else r
            g = random.uniform(50,255) if g == -1 else g
            b = random.uniform(50,255) if b == -1 else b
            self.plots[key] = (self.axes.plot(
              self.data[key], 
              linewidth=1,
              color=(r/255.0, g/255.0, b/255.0),
              label=str(key))[0])
            self.axes.legend(loc=2, prop={'size':8})
        else:
          self.data[key].append(value)
        
    def draw_plot(self):
        """ Redraws the plot
        """
        # when xmin is on auto, it "follows" xmax to produce a 
        # sliding window effect. therefore, xmin is assigned after
        # xmax.
        #
        if self.xmax_control.is_auto():
            xmax = max(50, max([len(x.get_xdata()) for x in self.plots.values()])) if self.data.keys() else 50
        else:
            xmax = int(self.xmax_control.manual_value())
            
        if self.xmin_control.is_auto():            
            xmin = xmax - 50
        else:
            xmin = int(self.xmin_control.manual_value())

        # for ymin and ymax, find the minimal and maximal values
        # in the data set and add a mininal margin.
        # 
        # note that it's easy to change this scheme to the 
        # minimal/maximal value in the current display, and not
        # the whole data set.
        # 
        ydata =[x.get_ydata()[-50:] for x in self.plots.values()]
        if self.ymin_control.is_auto():
            ymin = round(min((map(min, ydata))), 0) - 1
        else:
            ymin = int(self.ymin_control.manual_value())
        
        if self.ymax_control.is_auto():
            ymax = round(max(map(max, ydata)), 0) + 1
        else:
            ymax = int(self.ymax_control.manual_value())

        self.axes.set_xbound(lower=xmin, upper=xmax)
        self.axes.set_ybound(lower=ymin, upper=ymax)
        
        # anecdote: axes.grid assumes b=True if any other flag is
        # given even if b is set to False.
        # so just passing the flag into the first statement won't
        # work.
        #
        if self.cb_grid.IsChecked():
            self.axes.grid(True, color='gray')
        else:
            self.axes.grid(False)

        # Using setp here is convenient, because get_xticklabels
        # returns a list over which one needs to explicitly 
        # iterate, and setp already handles this.
        #  
        pylab.setp(self.axes.get_xticklabels(), 
            visible=self.cb_xlab.IsChecked())
        
        if not self.paused: # Don't update graph if paused.
          for key in self.data.keys():
              self.plots[key].set_xdata(np.arange(len(self.data[key])))
              self.plots[key].set_ydata(np.array(self.data[key]))
        
        self.canvas.draw()
    
    def on_pause_button(self, event):
        self.paused = not self.paused
    
    def on_update_pause_button(self, event):
        label = "Resume" if self.paused else "Pause"
        self.pause_button.SetLabel(label)
    
    def on_cb_grid(self, event):
        self.draw_plot()
    
    def on_cb_xlab(self, event):
        self.draw_plot()
    
    def on_save_plot(self, event):
        file_choices = "PNG (*.png)|*.png"
        
        dlg = wx.FileDialog(
            self, 
            message="Save plot as...",
            defaultDir=os.getcwd(),
            defaultFile="plot.png",
            wildcard=file_choices,
            style=wx.SAVE)
        
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            self.canvas.print_figure(path, dpi=self.dpi)
            self.flash_status_message("Saved to %s" % path)
    
    def on_redraw_timer(self, event):
        # if paused do not add data, but still redraw the plot
        # (to respond to scale modifications, grid change, etc.)
        # -- This is now handled in draw_plot()
        #if not self.paused:
        #    self.data.append(self.datagen.next())
        for cb in self.timer_callbacks:
            cb()
        self.draw_plot()
        
    def on_exit(self, event):
        # save data in a separate directory for each run
        savedir = datetime.now().strftime("data/%Y-%m-%d_%H-%M-%S")
        print "Saving data to", savedir
        if not os.path.exists(savedir):
            os.makedirs(savedir)
        for key, val in self.data.items():
            np.savetxt(os.path.join(savedir, key+'.csv'), np.array(val), delimiter=',\t')
        self.Destroy()
    
    def flash_status_message(self, msg, flash_len_ms=1500):
        self.statusbar.SetStatusText(msg)
        self.timeroff = wx.Timer(self)
        self.Bind(
            wx.EVT_TIMER, 
            self.on_flash_status_off, 
            self.timeroff)
        self.timeroff.Start(flash_len_ms, oneShot=True)
    
    def on_flash_status_off(self, event):
        self.statusbar.SetStatusText('')

    def register_callback(self, cb):
        self.timer_callbacks.append(cb)

class RandomPlotter(object):
    num_randoms = 0
    def __init__(self, frame):
        self.frame = frame
        self.datagen = DataGen()
        RandomPlotter.num_randoms = RandomPlotter.num_randoms + 1
        self.key = "Rand{0}".format(RandomPlotter.num_randoms)
        frame.register_callback(self.append_random)
        
    def append_random(self):
        self.frame.plot_value(self.key, self.datagen.next())
        
class SerialPlotter(object):
    def __init__(self, frame, port=6, baud=38400):
        self.frame = frame
        self.ser = serial.Serial(port, baud, timeout=1)
        TIMER_ID = 123
        self.timer = wx.Timer(frame, TIMER_ID)
        self.timer.Start(1)
        wx.EVT_TIMER(frame, TIMER_ID, self.time)

    def time(self, event):
        while self.ser.inWaiting() > 0: # Get everything in input buffer
            self.read_line()
    
    def parse_line(self, s):
        l = [tuple(entry.split(":")) for entry in s.split(",")]
        for k, v in l:
            self.frame.plot_value(k, int(v))

    def close_port(self):
        print 'Closing port'
        self.ser.close()
        
    def open_port(self):
        self.ser.open()
    
    def read_line(self):
      s = self.ser.readline()
      print s
      self.parse_line(s)
      
def parse_args():
    parser = argparse.ArgumentParser(description="""Plots values taken from serial input.
    Lines should be formatted like 'KEY1:%d,KEY2:%d' where KEY is the name of
    the data series.
    Saves data to CSV files in the data/ directory in a directory named by
    the time that you close the program, on exit.""")
    parser.add_argument('-t', '--test', action='store_true',
                        help='Test with random data instead of serial')
    parser.add_argument('-n', '--numtests', type=int, default=1,
                        help='Number of random test inputs')
    parser.add_argument('-p', '--port', type=int, default=7,
                        help='COM port number to use')
    parser.add_argument('-b', '--baud', type=int, default=115200,
                        help='baud rate')
    return parser.parse_args()

if __name__ == '__main__':
    args = parse_args()
    
    app = wx.PySimpleApp()
    app.frame = GraphFrame()
    if args.test:
        for x in xrange(args.numtests):
            rp = RandomPlotter(app.frame)
    else:
        sp = SerialPlotter(app.frame, args.port - 1, args.baud)
    
    app.frame.Show()
    app.MainLoop()
    if not args.test:
        sp.close_port()
