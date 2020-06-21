'''Desktop floating frame
'''
import keyboard
import win32gui
from PyQt5.QtCore import Qt
from PyQt5 import QtCore, QtGui, QtWidgets

from sigmaris.utils import loadUI, runInMainThread, Timer, setWindowTopMost, readPosition, writePosition
from sigmaris.task import task, StatusAction
from sigmaris.menu import ExMenu
from sigmaris.effect import AnimationShadowEffect
from sigmaris.query import QueryResult, DetectionInfo
from sigmaris.launch import startSigmaDiscover
from sigmaris.capture import ScreenCapture
from sigmaris.config import appConfig
from sigmaris.web import init_token_config, init_token_timer
from sigmaris.constants import WAITING_VALUE, FAILED_VALUE, DEFAULT_VALUE, DISEASE_VALUE, RUNNING_VALUE, HEALTH_VALUE


_translate = QtCore.QCoreApplication.translate


class SuspendFrame(QtWidgets.QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = loadUI(':/12sigma/frame', self)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setWindowFlags(self.windowFlags() | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)

        self._returnPressed = False
        self._returnedText = ''
        self._lastText = ''
        self._keyboardHandler = None
        self._queryResult = None    # type: QueryResult
        self._defaultPart = None    # type: DetectionInfo
        self._currentDetect = None
        self.capture = ScreenCapture(self)
        self.capture.foundTextAndStatus.connect(self._onGetResult)

        self.initMenu()
        self.initTray()

        self.ui.btnControl.clicked.connect(self._onButtonClicked)
        self.ui.lineEdit.textEdited.connect(self._onTextEdited)
        self.ui.lineEdit.editingFinished.connect(self._onEditFinished)
        self.ui.lineEdit.returnPressed.connect(self._onReturnPressed)

        self._editAnimation = AnimationShadowEffect(Qt.cyan, self.ui.lineEdit)
        self.ui.lineEdit.setGraphicsEffect(self._editAnimation)

        self.stateTimer = Timer(self._onStateTimer, 5000)
        self.stateTimer.start()

        self.info = None
        self.dragPostiton = QtCore.QPoint(0, 0)
        self.lastPosition = QtCore.QPoint(0, 0)
        task.statusGetted.connect(self._onGetStatus)
        task.priorityRaised.connect(self._onRaisedPriority)
        self.installShortcut()

        self.foregroundTimer = Timer(self._onForegroundTimer, 2500)
        self.foregroundTimer.start()
        setWindowTopMost(int(self.winId()), force=True)
        readPosition(self)
        init_token_timer(self)

    def _onForegroundTimer(self):
        if self.isHidden():
            self.raise_()
            self.show()
        activeWin = QtWidgets.QApplication.activeWindow()
        if not activeWin:
            wid = int(self.winId())
            if win32gui.GetForegroundWindow() != wid:
                self.setFocus()
                setWindowTopMost(wid)

    @property
    def currentId(self):
        return self.ui.lineEdit.text().strip()

    @currentId.setter
    def currentId(self, value):
        self.ui.lineEdit.setText(value)
        self.ui.lineEdit.home(False)

    def _setStatusValue(self, value):
        if value == self.property('status'):
            return
        button = self.ui.btnControl
        self.setProperty('status', value)
        self.style().unpolish(button)
        self.style().polish(button)
        button.update()

    def polishStatus(self):
        if self._queryResult:
            self._currentDetect = self._queryResult.getOne(self._defaultPart)
            value = self._currentDetect.value()
        else:
            value = FAILED_VALUE
            self._currentDetect = None
        self._setStatusValue(value)

    def resetStatus(self):
        self._queryResult = None
        self._setStatusValue(DEFAULT_VALUE)
        self._menu.initDetection([])

    def changeStatus(self, result):
        self._queryResult = result
        if not result:
            detections = []
        else:
            detections = result.detections
        self.polishStatus()
        self._menu.initDetection(detections)

    def queryStatus(self, edit=False):
        if not self.currentId:
            return
        if self._queryResult and self._queryResult.allDone():
            return
        if edit or self._returnPressed:
            action = StatusAction(edit=edit, open=self._returnPressed)
        else:
            action = None
        task.submitStatus(self.currentId, action)

    def _onTextEdited(self, text):
        self.resetStatus()

    def _onEditFinished(self):
        if not self.currentId:      # reset cache to refresh ocr
            self.capture.screenshot = None
        # self.resetStatus()
        self.queryStatus(edit=True)
        self._returnPressed = False

    def _onReturnPressed(self):
        self._returnPressed = True
        self._returnedText = self.currentId
        self.ui.lineEdit.blockSignals(True)
        self.setFocus(True)
        self.ui.lineEdit.blockSignals(False)

    def _onStateTimer(self):
        if not self.ui.lineEdit.hasFocus():
            self.queryStatus()

    def _onButtonClicked(self):
        if self.property('status') == WAITING_VALUE:
            task.submitRaise(self._currentDetect.job_id)
        else:
            self._openSigmaApp()

    def _onGetResult(self, result):
        self.currentId = result[0]
        currentText = self.currentId
        if currentText != self._lastText:    # only handle first same ocr, others use state timer
            # self.resetStatus()
            self.changeStatus(result[1])
            self._showMessage()
            self._editAnimation.start()
            self._lastText = currentText
            if appConfig['Launcher'].get('options', {}).get('autoOpen', False):
                self._openSigmaApp()

    def _onGetStatus(self, result):
        _result, _action = result
        self.changeStatus(_result)
        if not _action:
            return
        if _action.edit:
            self._showMessage()
        if _action.open and self._returnedText == self.currentId:
            self._openSigmaApp()

    def _onRaisedPriority(self, result):
        if not self._currentDetect and self._currentDetect.job_id != result.get('_job_id'):
            return
        self._currentDetect.job_id = result.get('job_id')
        self._currentDetect.order_number = result.get('order_number')
        self._currentDetect.wait_time = result.get('wait_time')
        self._showMessage()

    def _showMessage(self):
        if not self._queryResult:
            self.message('*未找到，是否识别有误!')
        else:
            detection = self._queryResult.getOne(self._defaultPart)     # type: DetectionInfo
            value = detection.value()
            if value == WAITING_VALUE:
                self.message('目前排第{}，需要等待{}分钟'.format(detection.order_number, detection.wait_time))
            elif value == FAILED_VALUE:
                self.message('很遗憾，sigma开小差了...')
            elif value == RUNNING_VALUE:
                self.message('正在计算，请稍后')
            # if detection.detect_type != self._defaultPart:
            #     pass

    def onMousePress(self, e):
        self.dragPostiton = e.pos()
        self.lastPosition = self.pos()

    def onMouseMove(self, e):
        pt = QtCore.QPoint(e.pos() - self.dragPostiton + self.pos())
        self.move(pt)

    def mouseMoveEvent(self, e):
        super().mouseMoveEvent(e)
        if e.buttons() & Qt.LeftButton:
            self.onMouseMove(e)

    def mousePressEvent(self, e):
        super().mousePressEvent(e)
        if e.button() == Qt.LeftButton:
            self.onMousePress(e)

    def uninstallShortcut(self):
        if self._keyboardHandler:
            keyboard.remove_hotkey(self._keyboardHandler)
            self._keyboardHandler = None

    def installShortcut(self):
        self.uninstallShortcut()
        if appConfig['OCR'].get('manualMode', True):
            shorcut = appConfig['OCR']['manual']['shortcut']
            if shorcut:
                self._keyboardHandler = keyboard.add_hotkey(shorcut, self._manualCapture, suppress=True)

    def _manualCapture(self):
        runInMainThread(lambda: QtCore.QTimer.singleShot(300, self.capture.selectionCapture))

    def initTray(self):
        self._tray = QtWidgets.QSystemTrayIcon(QtGui.QIcon(':/12sigma/tray'), self)
        self._tray.setToolTip('SigmaRIS')
        self._tray.setContextMenu(self._menu.trayMenu)
        # self._tray.activated.connect(self.__iconActivated)    # Can active app
        self._tray.show()

    def initMenu(self):
        self._menu = ExMenu(self)
        self.ui.btnControl.registerMenu(self._menu)
        self._menu.preSetting.connect(self._onPreSettings)
        self._menu.postSetting.connect(self._onPostSettings)
        self._menu.quitApplication.connect(self._onQuitApp)
        self._menu.openDetection.connect(self._onOpenDiscover)

    def message(self, note):
        self.ui.tipsLabel.notify(note, self.ui.container.y()+self.ui.container.height())

    def _onOpenDiscover(self, bodyPart):
        self._defaultPart = bodyPart
        self.polishStatus()
        self._showMessage()
        self._openSigmaApp()

    def _openSigmaApp(self):
        if not self.currentId or not self._currentDetect:
            return
        # if self._currentDetect.value() == DISEASE_VALUE:
        #     pass
        if self._currentDetect.status == "succeed":
            self.message('正在打开...')
            startSigmaDiscover(self._currentDetect)
        else:
            self._showMessage()

    def _onPreSettings(self):
        self.capture.setAutoMode(False)
        self.uninstallShortcut()

    def _onPostSettings(self):
        self.capture.setAutoMode(True)
        confirmTime = 1000 * appConfig['OCR']['manual']['timeout']
        self.capture.overlay.setTimerInterval(confirmTime)
        self.installShortcut()
        init_token_config()

    def _onQuitApp(self):
        writePosition(self)
        self._tray.hide()
        QtWidgets.QApplication.instance().exit()
