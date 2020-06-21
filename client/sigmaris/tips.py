from PyQt5 import QtCore, QtWidgets


class TipsLabel(QtWidgets.QLabel):
    '''Animation Tips Label'''

    def __init__(self, parent=None):
        super().__init__(parent)
        self._progress = 0
        self._yEnd = 0
        self._yBegin = 0
        self.animation = QtCore.QPropertyAnimation(self, b'progress')
        self.animation.setDuration(3000)

    def notify(self, text, y):
        self.setText(text)
        self._yEnd = y
        self._yBegin = self._yEnd - self.height()
        self.animation.setStartValue(0)
        self.animation.setKeyValueAt(0.1, 10)
        self.animation.setKeyValueAt(0.9, 10)
        self.animation.setEndValue(0)
        self.animation.start()

    def _getProgress(self):
        return self._progress

    def _setProgress(self, value):
        y = self._yBegin + value/10*self.height()
        # self.move(self.x(), y)
        if self.y() != y:
            self.move(self.x(), y)

    progress = QtCore.pyqtProperty(int, _getProgress, _setProgress)
