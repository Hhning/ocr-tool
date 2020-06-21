import re
import ctypes
import logging
import subprocess

import win32gui
import pywintypes
from PyQt5 import QtCore

from sigmaris.config import appConfig
from sigmaris.web import open_url

_logger = logging.getLogger(__name__)


def activeWindow(handle):
    try:
        win32gui.ShowWindow(handle, 4)
        win32gui.SetForegroundWindow(handle)
    except:
        pass


def findDiscover(title_re='sigma-discover Research*'):
    handle = None
    title_regex = re.compile(title_re)
    def enum_window_proc(hwnd, lparam):
        title = win32gui.GetWindowText(hwnd)
        if title_regex.match(title):
            nonlocal handle
            handle = hwnd
            return False
        else:
            return True
    enum_win_proc_t = ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.c_long, ctypes.c_long)
    proc = enum_win_proc_t(enum_window_proc)
    try:
        win32gui.EnumWindows(proc, 0)
    except pywintypes.error:
        pass

    if handle is not None:
        activeWindow(handle)


def startSigmaDiscover(info):
    config = appConfig['Launcher']
    launcherType = config['type']

    if launcherType == 'Web':
        return open_url(info.series_id)

    launcherPath = config['path'][launcherType]
    launcherParams = config['params'][info.detect_type]
    if not launcherType or not launcherPath:
        return
    templateData = {'path': launcherPath}
    try:
        templateData['params'] = launcherParams.format(info.series_id)
    except:
        templateData['params'] = launcherParams.format(**info.__dict__)
    command = config['command'][launcherType].format(**templateData)
    _logger.info('Launcher: {}'.format(command))
    subprocess.Popen(command, shell=True)
    QtCore.QTimer.singleShot(2000, findDiscover)
