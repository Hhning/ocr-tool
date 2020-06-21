import sys
import warnings

import win32gui
from PyQt5 import QtWidgets, QtGui, QtCore


if __name__ == '__main__':
    title = '%12Sigma-PACS/RIS?'          # must unique title for single application
    handle = win32gui.FindWindow(None, title)   # Qt5QWindowToolSaveBits
    if handle:
        win32gui.SetForegroundWindow(handle)
        warnings.warn('The application is already running!')
        sys.exit(0)

    from sigmaris import SuspendFrame
    from sigmaris.utils import loadRes

    app = QtWidgets.QApplication(sys.argv)
    app.setWindowIcon(QtGui.QIcon(":/12sigma/icon"))
    translator = QtCore.QTranslator()
    qtTranslator = QtCore.QTranslator()
    uiLanguages = QtCore.QLocale.system().uiLanguages()
    for locale in uiLanguages:
        _locale = QtCore.QLocale(locale).name()
        if translator.load(':/12sigma/{}'.format(_locale)):
            app.installTranslator(translator)
            if qtTranslator.load(':/12sigma/qt_{}'.format(_locale)):
                app.installTranslator(qtTranslator)
                break
            translator.load('')
        elif _locale == 'C' or _locale == 'en':
            break
    app.setQuitOnLastWindowClosed(False)
    app.setStyleSheet(loadRes(":/12sigma/style"))
    frame = SuspendFrame()
    frame.setWindowTitle(title)
    frame.show()
    app.exec_()
