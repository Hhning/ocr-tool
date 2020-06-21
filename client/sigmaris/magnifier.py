'''Magnifier'''
import logging
import time

from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtWidgets import QApplication
import keyboard

from sigmaris.utils import runInMainThread


_logger = logging.getLogger(__name__)


class Magnifier(QtWidgets.QWidget):
    centerDone = QtCore.pyqtSignal(QtCore.QPoint)
    centerCanceled = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("12Sigma - Magnifier")
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowStaysOnTopHint | QtCore.Qt.Tool)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.setMouseTracking(True)
        self._pixmap = None
        self._kbHandler = None
        self._timer = QtCore.QTimer()
        self._timer.setInterval(20)
        self._timer.timeout.connect(self._update)
        self.resize(140, 140)

    def _onActivated(self):
        self.close()
        self.centerDone.emit(QtGui.QCursor.pos())

    def _update(self):
        pos = QtGui.QCursor.pos()
        index = QApplication.desktop().screenNumber(pos)
        screen = QApplication.screens()[index]
        w = h = 20
        x = pos.x() - 10
        y = pos.y() - 10
        pixmap = screen.grabWindow(0, x, y, w, h).copy()
        if pixmap != self._pixmap:
            self._pixmap = pixmap
            self.repaint()

    def paintEvent(self, e):
        if not self._pixmap:
            return
        pos = QtGui.QCursor.pos()
        x, y = pos.x(), pos.y()
        painter = QtGui.QPainter(self)
        painter.setRenderHints(QtGui.QPainter.Antialiasing | QtGui.QPainter.HighQualityAntialiasing)
        painter.setPen(QtGui.QPen(QtCore.Qt.green, 1))
        brush = QtGui.QBrush(self._pixmap)
        transfrom = QtGui.QTransform()
        transfrom.scale(7.5, 7.5)
        brush.setTransform(transfrom)
        painter.setBrush(brush)
        painter.drawEllipse(0, 0, 140, 140)
        self.move(x + 20, y - 20)

    def showEvent(self, e):
        self._timer.start()
        if self._kbHandler:
            keyboard.unhook_key(self._kbHandler)
            self._kbHandler = None
        # add_hotkey can cause windows keyboard exception on keyboad-0.11.0
        # add_hotkey 'ctrl' invaild on keyboard-0.13.2
        # hook_key 'ctrl' invaild after sometimes on keyboard-0.13.2
        self._kbHandler = keyboard.hook_key('ctrl', lambda: runInMainThread(self._onActivated))

    def hideEvent(self, e):
        self._timer.stop()
        if self._kbHandler:
            keyboard.unhook_key(self._kbHandler)
            self._kbHandler = None
