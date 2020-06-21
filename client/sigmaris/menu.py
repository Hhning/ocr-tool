import functools

from PyQt5 import QtCore, QtGui, QtWidgets

from sigmaris.settings import SettingsDialog
from sigmaris.handbook import HandBookWidget

_translate = QtCore.QCoreApplication.translate


class ExMenu(QtWidgets.QMenu):

    openDetection = QtCore.pyqtSignal(str)
    preSetting = QtCore.pyqtSignal()
    postSetting = QtCore.pyqtSignal()
    quitApplication = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._moreMenu = None
        self._settingDlg = None
        self._handBookWidget = None
        # self.initDetection(['lung_nodule_det'])
        self._sep = self.addSeparator()
        self.initMore()

    def initMore(self):
        if self._moreMenu:
            return
        self._moreMenu = self.addMenu(_translate('12sigma.menu', 'More'))
        docAction = QtWidgets.QAction(_translate('12sigma.menu', 'Handbook'), self)
        setAction = QtWidgets.QAction(_translate('12sigma.menu', 'Settings'), self)
        exitAction = QtWidgets.QAction(_translate('12sigma.menu', 'Exit'), self)
        self._moreMenu.addAction(docAction)
        self._moreMenu.addAction(setAction)
        self._moreMenu.addSeparator()
        self._moreMenu.addAction(exitAction)

        setAction.triggered.connect(self._onSetting)
        docAction.triggered.connect(self._onHandBook)
        exitAction.triggered.connect(self.quitApplication.emit)

    def initDetection(self, detections):
        actions = self.actions()
        if len(actions) > 2:
            for a in actions[-3::-1]:
                self.removeAction(a)
        dActions = []
        for detection in detections:
            # action = self.addAction(QtGui.QIcon(':/12sigma/{}'.format(detection)), _translate('12sigma.detection', detection))
            action = QtWidgets.QAction(QtGui.QIcon(':/12sigma/{}'.format(detection)), _translate('12sigma.detection', detection), self)
            action.triggered.connect(functools.partial(self.openDetection.emit, detection))
            dActions.append(action)
        if dActions:
            self.insertActions(self._sep, dActions)

    @property
    def trayMenu(self):
        return self._moreMenu

    def _onSetting(self):
        if self._settingDlg is None:
            self._settingDlg = SettingsDialog()
            self._settingDlg.settingsClosed.connect(self.postSetting.emit)
        self.preSetting.emit()
        if not self._settingDlg.isVisible():
            self._settingDlg.updateUI()
        self._settingDlg.show()
        self._settingDlg.raise_()
        self._settingDlg.activateWindow()

    def _onHandBook(self):
        if self._handBookWidget is None:
            self._handBookWidget = HandBookWidget()
        self._handBookWidget.show()
