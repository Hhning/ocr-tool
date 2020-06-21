import functools

import win32gui
import pywintypes
from PyQt5 import QtWidgets, QtGui, QtCore, uic


SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOACTIVATE = 0x0010
SW_SHOWNOACTIVATE = 4
HWND_TOP = 0
HWND_TOPMOST = -1


class Signal:

    def __init__(self, *args, **kwargs):
        class _Object(QtCore.QObject):
            signal = QtCore.pyqtSignal(*args, **kwargs)
        self._object = _Object()
        self.connect = self._object.signal.connect
        self.disconnect = self._object.signal.disconnect
        self.emit = self._object.signal.emit

    def slot(self, slot):
        self.connect(slot)
        return slot

_workSignal = Signal(object)
_workSignal.connect(lambda x: x(), QtCore.Qt.BlockingQueuedConnection)


class Timer(object):

    def __init__(self, slot, msec=None):
        self._slot = slot
        self._msec = msec
        self._paused = True

    def start(self, msec=None):
        self.stop()
        if msec is not None and msec >= 0:
            self._msec = msec
        if self._msec >= 0:
            self._paused = False
            QtCore.QTimer.singleShot(self._msec, self._process)

    def stop(self):
        self._paused = True

    def _process(self):
        if self._paused:
            return
        self._slot()
        self.start(self._msec)


def runInMainThread(func, *args, **kwargs):
    app = QtWidgets.QApplication.instance()

    if QtCore.QThread.currentThread() is app.thread():
        return func(*args, **kwargs)

    result = None

    def helper():
        nonlocal result
        result = func(*args, **kwargs)
    _workSignal.emit(helper)
    return result


def loadRes(path):
    f = QtCore.QFile(path)
    f.open(QtCore.QFile.ReadOnly | QtCore.QFile.Text)
    ts = QtCore.QTextStream(f)
    ts.setCodec("utf-8")
    return ts.readAll()


def screenshot(x, y, w, h, buffer=True):
    index = QtWidgets.QApplication.desktop().screenNumber(QtCore.QPoint(x, y))
    screen = QtWidgets.QApplication.screens()[index]
    pixmap = screen.grabWindow(0, x, y, w, h).copy()
    if not buffer:
        return pixmap
    buffer = QtCore.QBuffer()
    buffer.open(QtCore.QBuffer.ReadWrite)
    pixmap.save(buffer, 'png')
    return buffer.data()


def loadUI(path, widget):
    f = QtCore.QFile(path)
    f.open(QtCore.QFile.ReadOnly | QtCore.QFile.Text)
    ts = QtCore.QTextStream(f)
    ts.setCodec("utf-8")
    return uic.loadUi(ts, widget)


def singleton(cls):
    '''singleton decorator'''
    _instance = {}

    @functools.wraps(cls)
    def instance(*args, **kwargs):
        if cls not in _instance:
            _instance[cls] = cls(*args, **kwargs)
        return _instance[cls]
    return instance


def bringWindowToTop(wid, foreground=False):
    win32gui.SetWindowPos(wid, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE|SWP_NOSIZE)
    if foreground:
        try:
            win32gui.SetForegroundWindow(wid)
        except pywintypes.error as e:
            print('SetForegroundWindow error', e)


def setWindowTopMost(wid, force=False):
    if force:
        try:
            win32gui.SetForegroundWindow(wid)
        except:
            pass
    win32gui.SetWindowPos(wid, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE|SWP_NOSIZE|SWP_NOACTIVATE)
    win32gui.ShowWindow(wid, SW_SHOWNOACTIVATE)


def readPosition(frame):
    settings = QtCore.QSettings('12 Sigma', 'Sigma-RIS')
    position = settings.value('frame/position')
    if position is not None:
        s = QtWidgets.QApplication.desktop().screenNumber(position)
        if s != -1:
            frame.move(position)    # TODO maybe out of screen
            return
    screen = QtWidgets.QApplication.primaryScreen()
    geometry = screen.geometry()
    x = geometry.right() - frame.width() - 20
    y = geometry.y() + 20
    frame.move(x, y)


def writePosition(frame):
    x, y = frame.x(), frame.y()
    settings = QtCore.QSettings('12 Sigma', 'Sigma-RIS')
    settings.setValue("frame/position", QtCore.QPoint(x, y))


def isUserAdmin():
    # WARNING: requires Windows XP SP2 or higher!
    import ctypes
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        print("Admin check failed, assuming not an admin.")
        return False


def runAsAdmin(command=None, wait=True):
    import win32con, win32event, win32process
    from win32com.shell import shell, shellcon

    if type(command) not in (tuple, list):
        raise ValueError("command is not a sequence.")
    params = ' '.join(command[1:])      # TODO maybe IndexError
    procInfo = shell.ShellExecuteEx(nShow=win32con.SW_HIDE,
                              fMask=shellcon.SEE_MASK_NOCLOSEPROCESS,
                              lpVerb='runas',   # causes UAC elevation prompt.
                              lpFile=command[0],
                              lpParameters=params)

    if wait:
        procHandle = procInfo['hProcess']    
        obj = win32event.WaitForSingleObject(procHandle, win32event.INFINITE)
        rc = win32process.GetExitCodeProcess(procHandle)
    else:
        rc = None
    print('runAsAdmin return: {}'.format(rc))
    return rc
