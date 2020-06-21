'''Screenshot overlay'''
import logging

from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import Qt, QSize, QPoint, QRect, QRectF, QSizeF
from PyQt5.QtGui import QCursor, QPixmap, QPainter, QColor, QKeySequence, QBrush, QPen, QFont
from PyQt5.QtWidgets import QApplication

from sigmaris.constants import *


_logger = logging.getLogger(__name__)
_translate = QtCore.QCoreApplication.translate


class SelectionOverlay(QtWidgets.QWidget):
    crossShape = QtCore.Qt.CrossCursor
    openHandShape = QtCore.Qt.OpenHandCursor
    closedHandShape = QtCore.Qt.ClosedHandCursor
    verticalShape = QtCore.Qt.SizeVerCursor
    horizontalShape = QtCore.Qt.SizeHorCursor
    leftDiagonalShape = QtCore.Qt.SizeFDiagCursor
    rightDiagonalShape = QtCore.Qt.SizeBDiagCursor

    selectionDone = QtCore.pyqtSignal(QRect, QPixmap)
    selectionCanceled = QtCore.pyqtSignal()

    def __init__(self, timeout=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("12Sigma - Selection")
        self.remember = False
        self.capturing = False
        self.resetRubberBand()
        self.currentScreenNumber = QApplication.desktop().screenNumber(QCursor.pos())
        self.setWindowFlags(self.windowFlags() | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setMouseTracking(True)
        self.setCursor(SelectionOverlay.crossShape)
        self.screenshot = QPixmap()
        self.initTimer(timeout)

    def initTimer(self, timeout):
        if timeout:
            self.timer = QtCore.QTimer()
            self.timer.setInterval(timeout)
            self.timer.setSingleShot(True)
            self.timer.timeout.connect(self.onTimeout)
        else:
            self.timer = None

    def setTimerInterval(self, value):
        if not self.timer or self.timer.interval() == value:
            return
        self.timer.stop()
        self.timer.setInterval(value)

    def startTimer(self):
        if not self.timer or self.timer.interval() <= 0:
            return
        if not self.timer.isActive():
            self.timer.start()

    def stopTimer(self):
        if self.timer:
            self.timer.stop()

    def resetRubberBand(self):
        if not self.remember:
            self.selection = QRect(0, 0, 0, 0)
            self.lastSelection = QRect(0, 0, 0, 0)
        self.selectionBeforeDrag = QRect(0, 0, 0, 0)
        self.resizingFrom = MOUSE_OUT
        self.selRectStart = QPoint(0, 0)
        self.selRectEnd = QPoint(0, 0)
        self.rbDistX = 0
        self.rbDistY = 0
        self.drawingRubberBand = self.movingRubberBand = self.resizingRubberBand = False
        self.startedDrawingRubberBand = False

    def selectionCapture(self):
        if not self.capturing:
            self.updateScreenshot()
            self.showFullScreen()
            self.capturing = True
        else:
            self.raise_()
            self.activateWindow()

    def updateSelection(self, gRect):
        if not self.capturing:
            self.remember = True
            self.updateScreenshot(gRect.topLeft())
            self._convertCoorinate(gRect)
            self.showFullScreen()
            self.capturing = True
        else:
            self.raise_()
            self.activateWindow()

    def _convertCoorinate(self, gRect):
        screen = QApplication.screens()[self.currentScreenNumber]
        screenGeom = screen.geometry()
        w = QtWidgets.QWidget()     # only to map coordinate system
        w.setWindowState(Qt.WindowFullScreen)
        w.setGeometry(screenGeom)
        w.showFullScreen()
        w.close()
        point = w.mapFromGlobal(gRect.topLeft())
        w, h = gRect.width(), gRect.height()
        rect = QtCore.QRect(point.x(), point.y(), w, h)
        self.lastSelection = self.selection
        self.selection = rect

    def _selectionDone(self):
        self.close()
        self.remember = True
        self.selectionDone.emit(self.selection, self.screenshot)
        self.resetRubberBand()
        self.lastSelection = self.selection
        self.capturing = False

    def _selectionCanceled(self):
        self.close()
        self.selectionCanceled.emit()
        self.resetRubberBand()
        self.selection = self.lastSelection
        self.capturing = False

    def onTimeout(self):
        if self.selection.width() > 0 and self.selection.height() > 0:
            self._selectionDone()

    def checkIfRubberBandOutOfBounds(self):
        if self.selection.x() < 0:
            self.selection.moveTo(0, self.selection.y())
        if self.selection.y() < 0:
            self.selection.moveTo(self.selection.x(), 0)
        if self.selection.x() + self.selection.width() > self.width():
            self.selection.moveTo(self.width() - self.selection.width(), self.selection.y())
        if self.selection.y() + self.selection.height() > self.height():
            self.selection.moveTo(self.selection.x(), self.height() - self.selection.height())

    def checkMouseOverRubberBand(self, mousePos):
        padding_width = 3
        padding_height = 3
        hoverLeft = QRect(self.selection.x() - padding_width, self.selection.y() + padding_height, padding_width * 2, self.selection.height() - padding_height *2)
        hoverRight = QRect(self.selection.x() + self.selection.width() - padding_width, self.selection.y() + padding_height, padding_width*2, self.selection.height() - padding_height*2)
        hoverTop = QRect(self.selection.x() + padding_width, self.selection.y() - padding_height, self.selection.width() - padding_width*2, padding_height*2)
        hoverBottom = QRect(self.selection.x() + padding_width, self.selection.y() + self.selection.height() - padding_height, self.selection.width() - padding_width*2, padding_height*2)
        hoverTopLeft = QRect(self.selection.x() - padding_width, self.selection.y() - padding_height, padding_width * 2, padding_height * 2)
        hoverTopRight = QRect(self.selection.x() + self.selection.width() - padding_width, self.selection.y() - padding_height, padding_width*2, padding_height*2)
        hoverBottomLeft = QRect(self.selection.x() - padding_width, self.selection.y() + self.selection.height() - padding_height, padding_width*2, padding_height*2)
        hoverBottomRight = QRect(self.selection.x() + self.selection.width() - padding_width, self.selection.y() + self.selection.height() - padding_height, padding_width*2, padding_height*2)
        if self.selection.width() > 0 and self.selection.height() > 0:
            if hoverLeft.contains(mousePos):
                return MOUSE_OVER_LEFT
            if hoverRight.contains(mousePos):
                return MOUSE_OVER_RIGHT
            if hoverTop.contains(mousePos):
                return MOUSE_OVER_TOP
            if hoverBottom.contains(mousePos):
                return MOUSE_OVER_BOTTOM
            if hoverTopLeft.contains(mousePos):
                return MOUSE_OVER_TOPLEFT
            if hoverTopRight.contains(mousePos):
                return MOUSE_OVER_TOPRIGHT
            if hoverBottomLeft.contains(mousePos):
                return MOUSE_OVER_BOTTOMLEFT
            if hoverBottomRight.contains(mousePos):
                return MOUSE_OVER_BOTTOMRIGHT
            if mousePos.x() > self.selection.x() + 1 and mousePos.y() > self.selection.y() + 1 and mousePos.x() < self.selection.x() + self.selection.width() and mousePos.y() < self.selection.y() + self.selection.height():
                # Mouse is inside rubber band
                return MOUSE_OVER_INSIDE
            return MOUSE_OUT
        return MOUSE_OUT

    def updateScreenshot(self, pos=None):
        self.currentScreenNumber = QApplication.desktop().screenNumber(pos or QCursor.pos())
        self.moveToScreen(self.currentScreenNumber)   # Moving to the current screen to get a new screenshot

    def drawOverlay(self, painter, color):
        painter.save()
        rectBrush = QBrush(color, Qt.SolidPattern)
        painter.setBrush(rectBrush)
        painter.setPen(Qt.NoPen)
        if self.selection.width() > 0 and self.selection.height() > 0:
            left = QRectF(0, 0, self.selection.x(), self.selection.y() + self.selection.height())
            right = QRectF(self.selection.x()+ self.selection.width(), 0, self.width() - self.selection.width(), self.selection.y() + self.selection.height())
            top = QRectF(self.selection.x(), 0, self.selection.width(), self.selection.y())
            bottom = QRectF(0, self.selection.y() + self.selection.height(), self.width(), self.height() - self.selection.y())
            rects = [left, right, top, bottom]
            painter.drawRects(rects)
        else:
            fullScreen = QRectF(0, 0, self.width(), self.height())
            painter.drawRect(fullScreen)
        painter.restore()

    def drawRubberband(self, painter, rect, color, lineSize):
        painter.save()
        pen = QPen(color, lineSize, Qt.SolidLine, Qt.SquareCap)
        painter.setPen(pen)
        offset = -(lineSize / 2)
        if self.selection.width() > 0 and self.selection.height() > 0:
            drawRect = QRectF(rect)
            drawRect.setSize(QSizeF(rect.size().width() - offset, rect.size().height() - offset))
            drawRect.setX(drawRect.x() + offset)
            drawRect.setY(drawRect.y() + offset)
            painter.drawRect(drawRect)
        painter.restore()

    def drawHelpText(self, painter, bgColor, textColor):
        if self.remember:
            return
        if not self.startedDrawingRubberBand:
            painter.save()
            roundedRectBrush = QBrush(bgColor)
            roundedRectPen = QPen(roundedRectBrush, 1.0)
            textBrush = QBrush(textColor)
            f = QFont(QFont().defaultFamily(), 16, QFont.Normal)
            painter.setFont(f)
            helpTextRect = QRect(0, 0, 600, 90)
            helpText = _translate("12sigma.overlay", "Draw a rectangular area using the mouse.\nPress Enter to confirm or Esc to cancel.")
            if QApplication.desktop().screenCount() > 1:
                helpText += _translate("12sigma.overlay", "\nUse the arrow keys to switch between screens.")
                helpTextRect.setWidth(helpTextRect.width() + 30)
                helpTextRect.setHeight(helpTextRect.height() + 30)
            helpTextRect.moveCenter(self.mapFromGlobal(QApplication.desktop().screenGeometry(self.currentScreenNumber).center()))
            painter.setBrush(roundedRectBrush)
            painter.setPen(roundedRectPen)
            painter.drawRoundedRect(helpTextRect, 10.0, 10.0)
            painter.setBrush(textBrush)
            painter.setPen(QPen(textBrush, 1.0))
            painter.drawText(helpTextRect, Qt.AlignCenter, helpText)
            painter.restore()

    def moveToScreen(self, screenNumber):
        if screenNumber < 0:
            screenNumber = QApplication.desktop().screenCount() - 1
        elif screenNumber >= QApplication.desktop().screenCount():
            screenNumber = 0
        self.currentScreenNumber = screenNumber
        screenGeom = QRect()
        screen = QApplication.screens()[self.currentScreenNumber]
        screenGeom = screen.geometry()
        if not screenGeom.isValid() or screenGeom.isNull():
            _logger.warning("Failed to get geometry for screen {}".format(screenNumber))
        screenshot = screen.grabWindow(QApplication.desktop().winId(), screenGeom.x(), screenGeom.y(), screenGeom.width(), screenGeom.height()).copy()
        # screenshot = screen.grabWindow(0, screenGeom.x(), screenGeom.y(), screenGeom.width(), screenGeom.height()).copy()
        if screenshot.size() != screenGeom.size():
            _logger.info("Scaling screenshot to fit screenGeom")
            screenshot = screenshot.scaled(screenGeom.size(), Qt.KeepAspectRatio)
        self.screenshot = screenshot
        self.resetRubberBand()
        self.setWindowState(Qt.WindowFullScreen)
        self.setGeometry(screenGeom)

    def showEvent(self, e):
        self.raise_()
        self.repaint()
        self.activateWindow()
        self.setWindowState(Qt.WindowFullScreen)
        self.startTimer()

    def hideEvent(self, e):
        self.stopTimer()

    def paintEvent(self, e):
        painter = QPainter(self)
        painter.drawPixmap(0, 0, self.screenshot)
        self.drawOverlay(painter, QColor(100, 100, 100, 140))
        self.drawRubberband(painter, self.selection, QColor(227, 65, 51), 1)
        self.drawHelpText(painter, QColor(28, 28, 28, 220), QColor(127, 127, 127, 240))

    def mousePressEvent(self, event):
        self.activateWindow()
        # Stop the overlay from drawing help text
        self.startedDrawingRubberBand = True
        mousePos = event.pos()
        # Check if the mouse is over the rubber band
        if self.checkMouseOverRubberBand(mousePos) == MOUSE_OVER_INSIDE:
            self.movingRubberBand = True
            self.drawingRubberBand = False
            self.resizingRubberBand = False
            self.rbDistX = event.pos().x() - self.selection.x()
            self.rbDistY = event.pos().y() - self.selection.y()
            self.setCursor(SelectionOverlay.closedHandShape)
        elif self.checkMouseOverRubberBand(mousePos) == MOUSE_OVER_LEFT or self.checkMouseOverRubberBand(mousePos) == MOUSE_OVER_RIGHT or self.checkMouseOverRubberBand(mousePos) == MOUSE_OVER_TOP or self.checkMouseOverRubberBand(mousePos) == MOUSE_OVER_BOTTOM or self.checkMouseOverRubberBand(mousePos) == MOUSE_OVER_TOPLEFT or self.checkMouseOverRubberBand(mousePos) == MOUSE_OVER_TOPRIGHT or self.checkMouseOverRubberBand(mousePos) == MOUSE_OVER_BOTTOMLEFT or self.checkMouseOverRubberBand(mousePos) == MOUSE_OVER_BOTTOMRIGHT:
            self.resizingRubberBand = True
            self.drawingRubberBand = False
            self.movingRubberBand = False
            self.resizingFrom = self.checkMouseOverRubberBand(mousePos)
            self.selectionBeforeDrag = self.selection
        else:
            self.drawingRubberBand = True
            self.movingRubberBand = False
            self.resizingRubberBand = False
            self.selRectStart = event.pos()
        self.repaint()

    def mouseReleaseEvent(self, event):
        self.selRectEnd = event.pos()
        self.drawingRubberBand = False
        self.movingRubberBand = False
        self.resizingRubberBand = False
        self.repaint()

    def mouseMoveEvent(self, event):
        # Check if the mouse is over the rubber band
        self.stopTimer()
        mousePos = event.pos()
        if self.checkMouseOverRubberBand(mousePos) == MOUSE_OVER_INSIDE:
            # Mouse is over rubber band
            if not self.drawingRubberBand and not self.movingRubberBand and not self.resizingRubberBand:
                self.setCursor(SelectionOverlay.openHandShape)
            elif self.movingRubberBand:
                self.setCursor(SelectionOverlay.closedHandShape)
        # If the mouse is on the left side of the rubberband
        elif not self.movingRubberBand and not self.drawingRubberBand and (self.checkMouseOverRubberBand(mousePos) == MOUSE_OVER_LEFT or self.checkMouseOverRubberBand(mousePos) == MOUSE_OVER_RIGHT):
            self.setCursor(SelectionOverlay.horizontalShape)
        elif not self.movingRubberBand and not self.drawingRubberBand and (self.checkMouseOverRubberBand(mousePos) == MOUSE_OVER_TOP or self.checkMouseOverRubberBand(mousePos) == MOUSE_OVER_BOTTOM):
            self.setCursor(SelectionOverlay.verticalShape)
        elif not self.movingRubberBand and not self.drawingRubberBand and (self.checkMouseOverRubberBand(mousePos) == MOUSE_OVER_TOPLEFT or self.checkMouseOverRubberBand(mousePos) == MOUSE_OVER_BOTTOMRIGHT):
            self.setCursor(SelectionOverlay.leftDiagonalShape)
        elif not self.movingRubberBand and not self.drawingRubberBand and (self.checkMouseOverRubberBand(mousePos) == MOUSE_OVER_TOPRIGHT or self.checkMouseOverRubberBand(mousePos) == MOUSE_OVER_BOTTOMLEFT):
            self.setCursor(SelectionOverlay.rightDiagonalShape)
        elif not self.movingRubberBand and not self.resizingRubberBand:
            self.setCursor(SelectionOverlay.crossShape)
        if event.buttons() == Qt.LeftButton and self.movingRubberBand:
            self.selection.moveTo(event.pos().x() - self.rbDistX, event.pos().y() - self.rbDistY)
            self.checkIfRubberBandOutOfBounds()
        if event.buttons() == Qt.LeftButton and self.drawingRubberBand:
            self.selRectEnd = event.pos()
            self.selection = QRect(self.selRectStart, self.selRectEnd).normalized()
            self.selection = self.selection.intersected(self.rect())
        if event.buttons() == Qt.LeftButton and self.resizingRubberBand:
            if self.resizingFrom == MOUSE_OVER_LEFT:
                if self.selection.x() < self.selectionBeforeDrag.x() + self.selectionBeforeDrag.width():
                    self.resizeLeft(mousePos, self.selectionBeforeDrag)
                else:
                    self.resizingFrom = MOUSE_OVER_RIGHT
                    self.selectionBeforeDrag = self.selection
                    self.selection.moveTo(self.selectionBeforeDrag.topLeft())
            elif self.resizingFrom == MOUSE_OVER_RIGHT:
                if mousePos.x() > self.selectionBeforeDrag.x():
                    self.resizeRight(mousePos, self.selectionBeforeDrag)
                else:
                    self.resizingFrom = MOUSE_OVER_LEFT
                    self.selectionBeforeDrag = self.selection
            elif self.resizingFrom == MOUSE_OVER_TOP:
                if self.selection.y() < self.selectionBeforeDrag.y() + self.selectionBeforeDrag.height():
                    self.resizeTop(mousePos, self.selectionBeforeDrag)
                else:
                    self.resizingFrom = MOUSE_OVER_BOTTOM
                    self.selectionBeforeDrag = self.selection
                    self.selection.moveTo(self.selectionBeforeDrag.topLeft())
            elif self.resizingFrom == MOUSE_OVER_BOTTOM:
                if mousePos.y() > self.selection.y():
                    self.resizeBottom(mousePos, self.selectionBeforeDrag)
                else:
                    self.resizingFrom = MOUSE_OVER_TOP
                    self.selectionBeforeDrag = self.selection
            elif self.resizingFrom == MOUSE_OVER_TOPLEFT:
                if self.selection.x() < self.selectionBeforeDrag.x() + self.selectionBeforeDrag.width():
                    self.resizeTop(mousePos, self.selectionBeforeDrag)
                    self.resizeLeft(mousePos, self.selectionBeforeDrag)
                else:
                    self.resizingFrom = MOUSE_OVER_BOTTOMRIGHT
                    self.selectionBeforeDrag = self.selection
                    self.selection.moveTo(self.selectionBeforeDrag.topLeft())
            elif self.resizingFrom == MOUSE_OVER_TOPRIGHT:
                if mousePos.x() > self.selectionBeforeDrag.x():
                    self.resizeTop(mousePos, self.selectionBeforeDrag)
                    self.resizeRight(mousePos, self.selectionBeforeDrag)
                else:
                    self.resizingFrom = MOUSE_OVER_BOTTOMLEFT
                    self.selectionBeforeDrag = self.selection
            elif self.resizingFrom == MOUSE_OVER_BOTTOMLEFT:
                if mousePos.x() < self.selectionBeforeDrag.x() + self.selectionBeforeDrag.width():
                    self.resizeBottom(mousePos, self.selectionBeforeDrag)
                    self.resizeLeft(mousePos, self.selectionBeforeDrag)
                else:
                    self.resizingFrom = MOUSE_OVER_TOPRIGHT
                    self.selectionBeforeDrag = self.selection
            elif self.resizingFrom == MOUSE_OVER_BOTTOMRIGHT:
                if mousePos.x() > self.selectionBeforeDrag.x():
                    self.resizeBottom(mousePos, self.selectionBeforeDrag)
                    self.resizeRight(mousePos, self.selectionBeforeDrag)
                else:
                    self.resizingFrom = MOUSE_OVER_TOPLEFT
                    self.selectionBeforeDrag = self.selection
        if self.selection.width() < 0 or self.selection.height() < 0:
            self.selection = self.selection.normalized()
        if self.drawingRubberBand or self.movingRubberBand or self.resizingRubberBand:
            self.repaint()
        self.selection = self.selection.intersected(self.rect())
        self.startTimer()

    def mouseDoubleClickEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            self._selectionDone()

    # def keyPressEvent(self, event):       # Adjust the location with the keyboard, if we need, please change switch screen shortcut
    #     singleStep = 0
    #     if event.modifiers() == Qt.NoModifier:
    #         singleStep = 1      # low speed
    #     elif event.modifiers() == Qt.ShiftModifier:
    #         singleStep = 10     # fast speed
    #     if singleStep >= 1:
    #         x, y = self.selection.x(), self.selection.y()
    #         if event.key() == Qt.Key_Up:
    #             y -= singleStep
    #         elif event.key() == Qt.Key_Down:
    #             y += singleStep
    #         elif event.key() == Qt.Key_Left:
    #             x -= singleStep
    #         elif event.key() == Qt.Key_Right:
    #             x += singleStep
    #         self.selection.moveTo(x, y)
    #         self.checkIfRubberBandOutOfBounds()
    #         if self.selection.width() < 0 or self.selection.height() < 0:
    #             self.selection = self.selection.normalized()
    #         self.repaint()
    #         self.selection = self.selection.intersected(self.rect())
    #     super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        if event.matches(QKeySequence.Save) or event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            self._selectionDone()
        elif event.matches(QKeySequence.Quit) or event.key() == Qt.Key_Escape:
            self._selectionCanceled()
        elif event.key() == Qt.Key_Left:
            if QApplication.desktop().screenCount() > 1:
                self.moveToScreen(self.currentScreenNumber + 1)
        elif event.key() == Qt.Key_Right:
            if QApplication.desktop().screenCount() > 1:
                self.moveToScreen(self.currentScreenNumber - 1)
        super().keyReleaseEvent(event)

    def resizeLeft(self, mousePos, rbGeometryBeforeResize):
        self.selection.moveTo(mousePos.x(), self.selection.y())
        self.selection.setSize(QSize(rbGeometryBeforeResize.width() - (mousePos.x()- rbGeometryBeforeResize.x()), self.selection.height()))
        self.selection = self.selection.intersected(self.rect())

    def resizeTop(self, mousePos, rbGeometryBeforeResize):
        self.selection.moveTo(self.selection.x(), mousePos.y())
        self.selection.setSize(QSize(self.selection.width(), rbGeometryBeforeResize.height() - (mousePos.y()- rbGeometryBeforeResize.y())))
        self.selection = self.selection.intersected(self.rect())

    def resizeRight(self, mousePos, rbGeometryBeforeResize):
        self.selection.setSize(QSize(mousePos.x() - rbGeometryBeforeResize.x(), self.selection.height()))
        self.selection = self.selection.intersected(self.rect())

    def resizeBottom(self, mousePos, rbGeometryBeforeResize):
        self.selection.setSize(QSize(self.selection.width(), mousePos.y() - rbGeometryBeforeResize.y()))
        self.selection = self.selection.intersected(self.rect())
