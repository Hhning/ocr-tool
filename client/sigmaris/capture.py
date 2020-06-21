import os
import logging

from PyQt5.QtGui import QCursor
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QObject, QTimer, pyqtSignal, QPoint, QBuffer

from sigmaris.config import AppConfig, DEBUG_PATH, ROI_PATH
from sigmaris.overlay import SelectionOverlay
from sigmaris.task import task
from sigmaris.utils import Timer
from sigmaris.image import templateMatching, nparray2qimage

_logger = logging.getLogger(__name__)


class ScreenCapture(QObject):

    foundTextAndStatus = pyqtSignal(tuple)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.appConfig = AppConfig()
        self.screenshot = None
        # self.autoTimer = QTimer(self)
        # self.autoTimer.timeout.connect(self.autoCapture)
        self.autoTimer = Timer(self.autoCapture)
        confirmTime = 1000 * self.appConfig['OCR']['manual']['timeout']
        self.overlay = SelectionOverlay(timeout=confirmTime)
        self.overlay.selectionDone.connect(self.selectionDone)
        self.setAutoMode(True)
        task.pipelined.connect(self.onTextAndStatus)

    def _multiScreenshot(self):
        rects = self.appConfig['OCR']['automatic'].get('rect', [])
        images = []
        settings = []
        for rect in rects:
            x, y = rect['x'], rect['y']
            w, h = rect['w'], rect['h']
            if w <= 0 or h <= 0:
                continue
            s = QApplication.desktop().screenNumber(QPoint(x, y))
            image = self.imageCapture(x, y, w, h, s)
            if image:
                images.append(image)
                settings.append(rect)
        return images, settings

    def multiImage(self):
        screenshot, settings = self._multiScreenshot()
        if screenshot == self.screenshot:
            _logger.debug('screenshot no changed')
            return [], []
        images = []
        infos = []
        for image, setting in zip(screenshot, settings):
            if 'fc' in setting.keys():
                fc_path = os.path.join(ROI_PATH, setting['fc'])
                if not os.path.exists(fc_path):
                    continue
                cvImage = templateMatching(image, fc_path, setting)
                if cvImage is None:
                    continue
                image = nparray2qimage(cvImage)
            images.append(image)
            infos.append({'threshold': setting['t']})
        self.screenshot = screenshot
        return images, infos

    def autoCapture(self):
        if self.overlay.capturing:
            return
        if self.parent().ui.lineEdit.hasFocus():    # skip when inputting
            return
        images, infos = self.multiImage()
        if not images:
            return
        self.imageOCR(images, infos)

    def setAutoMode(self, enable):
        self.autoTimer.stop()
        interval = 1000 * self.appConfig['OCR']['automatic'].get('interval', 0)
        _enable = not self.appConfig['OCR'].get('manualMode', True)
        _interval = interval if interval > 1000 else 1000   # min interval 1000ms
        if enable and _enable:
            self.autoTimer.start(_interval)  # ms

    def imageOCR(self, images, infos=None):
        files = []
        data = {}
        for index, image in enumerate(images):
            buffer = QBuffer()
            buffer.open(QBuffer.ReadWrite)
            image.save(buffer, 'png')
            name = '{:02d}.png'.format(index)
            files.append((name, buffer.data()))
            if infos:
                for k, v in infos[index].items():
                    data['{}+{}'.format(k, name)] = v
            if self.appConfig.debug:
                image.save('{}/{}'.format(DEBUG_PATH, name))
        task.submitPipeline(files, data)

    def onTextAndStatus(self, text):
        if not self.parent().ui.lineEdit.hasFocus():
            self.foundTextAndStatus.emit(text)

    def imageCapture(self, x, y, width, height, screenNumber):
        try:
            screen = QApplication.screens()[screenNumber]
        except IndexError:
            _logger.error('Need reset location!')
            return
        _logger.debug('Auto - x: {}, y: {}, w: {}, h: {}, s: {}'.format(x, y, width, height, screenNumber))
        pixmap = screen.grabWindow(0, x, y, width, height).copy()
        screenshot = pixmap.toImage()
        return screenshot

    def selectionCapture(self):
        self.overlay.selectionCapture()
    
    def selectionDone(self, rect, pixmap):
        _logger.debug('Manual - rect: {}'.format(rect))
        screenshot = pixmap.copy(rect).toImage()
        frame = self.parent()
        editor = frame.ui.lineEdit
        editor.blockSignals(True)
        frame.setFocus()
        editor.blockSignals(False)
        self.imageOCR([screenshot])
