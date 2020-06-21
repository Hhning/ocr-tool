import os
import time
import tempfile

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt

from sigmaris.config import appConfig, ROI_PATH
from sigmaris.utils import loadUI, screenshot
from sigmaris.query import setupOCR
from sigmaris.image import templateMatching, nparray2bytearray


class BBoxDialog(QtWidgets.QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = loadUI(':/12sigma/bbox', self)
        self.valid = False
        self.setting = {}
        self.r1 = self.r2 = self.r3 = None
        self._template = None
        self.ui.checkButton.clicked.connect(self._check)
        self.ui.noPrefix.stateChanged.connect(self._onPrefixCheckChanged)
        self.ui.pixmapWidget.selectionChanged.connect(self._onChanged)
        self.ui.nextBtn.clicked.connect(self._nextStep)
        self.ui.prveBtn.clicked.connect(self._prveStep)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint | Qt.WindowStaysOnTopHint)

    def _nextStep(self):
        self.ui.stackedWidget.setCurrentIndex(1)
        self.ui.pixmapWidget.step = 1

    def _prveStep(self):
        self.ui.stackedWidget.setCurrentIndex(0)
        self.ui.pixmapWidget.step = 0

    def _onPrefixCheckChanged(self, state):
        if state == 2:
            self.ui.pixmapWidget.clearSelection()
            self._nextStep()

    def updatePixmap(self, x, y):
        self.ui.pixmapWidget.updatePixmap(x, y)

    def saveTemplate(self, name):
        if not self._template:
            return
        self._template.save(os.path.join(ROI_PATH, name), 'png')
        self._template = None

    def _updateRect(self):
        ret = False
        self.valid = False
        self.setting = {}
        self.r1 = self.r2 = self.r3 = None
        self._template = None
        self.ui.ocrResult.clear()
        if self.ui.noPrefix.isChecked():
            self.r2 = self.ui.pixmapWidget.getRect()
            ret = True
        else:
            try:
                r1, r2, r3 = self.ui.pixmapWidget.getRect2()
            except ValueError as e:
                self._showTips(str(e), '#ff0000')
            else:
                self.r1, self.r2, self.r3 = r1, r2, r3
                ret = True
        return ret

    def _onChanged(self):
        self._showTips('区域发生变化，请验证区域', '#EE7600')

    def _legacyImage(self):
        setting = {
            'x': self.r2.x(), 
            'y': self.r2.y(),
            'w': self.r2.width(), 
            'h': self.r2.height()
        }
        pidImage = screenshot(self.r2.x(), self.r2.y(), self.r2.width(), self.r2.height())
        return pidImage, setting

    def _templateImage(self):
        self._template = screenshot(self.r1.x(), self.r1.y(), self.r1.width(), self.r1.height(), buffer=False).toImage()
        preFile = tempfile.mkstemp()[1]
        self._template.save(preFile, 'png')
        bigImage = screenshot(self.r3.x(), self.r3.y(), self.r3.width(), self.r3.height(), buffer=False).toImage()
        setting = {
            'dx': self.r2.x() - self.r1.x(), 
            'dy': self.r2.y() - self.r1.y(),
            'dw': self.r2.width(), 
            'dh': self.r2.height(),
            'x': self.r3.x(), 
            'y': self.r3.y(),
            'w': self.r3.width(), 
            'h': self.r3.height(),
            'fc': '{}.png'.format(time.time())
        }
        cvImage = templateMatching(bigImage, preFile, setting)
        if cvImage is not None:
            pidImage = nparray2bytearray(cvImage)
        else:
            pidImage = None
        # os.remove(preFile)
        return pidImage, setting

    def _check(self):
        self.valid = False
        if not self._updateRect():
            return
        text = self.ui.manResult.text().strip()
        if not text:
            self._showTips('请输入正确结果', '#ff0000')
            return
        if self.r2.width() < 15 or self.r2.height() < 8:
            self._showTips('区域无效，请重新设置', '#ff0000')
            return
        image, setting = self._templateImage() if self.r1 else self._legacyImage()
        if not image:
            self._showTips('区域无效，请重新设置', '#ff0000')
            return
        files = [('00.png', image)]
        try:
            result = setupOCR(files, patient_id=text)     # TODO try except
        except:
            result = ''
        if isinstance(result, tuple):
            assert len(result) == 2
            result, setting['t'] = result
        self.ui.ocrResult.setText(result)
        if result == text:
            self.valid = True
            self.setting = setting
            self._showTips('区域有效，按"OK"确认')
        else:
            self._showTips('区域无效，请重新设置', '#ff0000')

    def _reset(self):
        self.ui.manResult.clear()
        self.ui.ocrResult.clear()

    def _showTips(self, text, color='#00aa00'):
        _text = '<html><head/><body><p><span style=" font-size:11pt; color:{};">{}</span></p></body></html>'.format(color, text)
        self.ui.resutlLabel.setText(_text)
        self.ui.resutlLabel.show()

    def _hideTips(self):
        self.ui.resutlLabel.hide()

    def showEvent(self, e):
        if self.ui.noPrefix.isChecked():
            self._nextStep()
        else:
            self._prveStep()

    def hideEvent(self, e):
        self._reset()
        self._hideTips()

    def accept(self):
        super().accept()

    def reject(self):
        self.valid = False
        super().reject()
