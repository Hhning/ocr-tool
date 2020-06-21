import math

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt, QSize, QPoint, QRect, QRectF, QSizeF
from PyQt5.QtGui import QCursor, QPainter, QColor, QKeySequence, QPen
from PyQt5.QtWidgets import QApplication

from sigmaris.constants import *
from sigmaris.config import appConfig


class EnlargedView(QtWidgets.QWidget):

    confirmFinished = QtCore.pyqtSignal(int, int, int, int)
    selectionChanged = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._x = 0
        self._y = 0
        self._w = 300
        self._h = 60
        self._pixmap = None
        self.step = 0
        self.setCursor(CROSS_SHAPE)
        self.resetRubberBand()
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)

    @property
    def selection(self):
        if self.step == 0:
            return self._preSelection
        return self._pidSelection

    @selection.setter
    def selection(self, value):
        if self.step == 0:
            self._preSelection = value
        else:
            self._pidSelection = value

    @property
    def selectionBeforeDrag(self):
        if self.step == 0:
            return self._preSelectionBeforeDrag
        return self._pidSelectionBeforeDrag

    @selectionBeforeDrag.setter
    def selectionBeforeDrag(self, value):
        if self.step == 0:
            self._preSelectionBeforeDrag = value
        else:
            self._pidSelectionBeforeDrag = value

    def clearSelection(self):
        if self.step == 0:
            self._preSelection = QtCore.QRect(0, 0, 0, 0)
        else:
            self._pidSelection = QtCore.QRect(0, 0, 0, 0)
        self.repaint()
    
    def updatePixmap(self, x, y):
        self._x = x
        self._y = y
        w = self._w
        h = self._h
        index = QtWidgets.QApplication.desktop().screenNumber(QtCore.QPoint(x, y))
        screen = QtWidgets.QApplication.screens()[index]
        self._pixmap = screen.grabWindow(0, x-w/2, y-h/2, w, h).copy()
        self.resetRubberBand()

    def getRect(self):
        ZOOM_IN_X_PIXEL = appConfig['OCR'].get('zoom', {}).get('x', 10)
        ZOOM_IN_Y_PIXEL = appConfig['OCR'].get('zoom', {}).get('y', 10)
        xScaled = self.width() / self._w
        yScaled = self.height() / self._h
        pidRect = QRect()
        pidRect.setX(self._x - self._w / 2 + math.floor(self.selection.x()/xScaled) - ZOOM_IN_X_PIXEL)
        pidRect.setY(self._y - self._h / 2 + math.floor(self.selection.y()/yScaled) - ZOOM_IN_Y_PIXEL)
        pidRect.setWidth(math.ceil(self.selection.width() / xScaled) + 2 * ZOOM_IN_X_PIXEL)
        pidRect.setHeight(math.ceil(self.selection.height() / yScaled) + 2 * ZOOM_IN_Y_PIXEL)
        return pidRect

    def getRect2(self):
        if self._preSelection.isNull():
            raise ValueError('特征区域为空')
        if self._pidSelection.isNull():
            raise ValueError('病例号区域为空')
        if self._pidSelection.intersects(self._preSelection):
            raise ValueError('区域重叠，请调整')
        if abs(self._pidSelection.center().y() - self._preSelection.center().y()) >= self._pidSelection.height()/2:
            raise ValueError('区域偏差较大，请调整')
        ZOOM_IN_X_PIXEL = appConfig['OCR'].get('zoom', {}).get('x', 10)
        ZOOM_IN_Y_PIXEL = appConfig['OCR'].get('zoom', {}).get('y', 10)
        xScaled = self.width() / self._w
        yScaled = self.height() / self._h
        ox = self._x - self._w / 2
        oy = self._y - self._h / 2
        pidRect = QRect()
        pidRect.setX(ox + math.floor(self._pidSelection.x()/xScaled) - ZOOM_IN_X_PIXEL)
        pidRect.setY(oy + math.floor(self._pidSelection.y()/yScaled) - ZOOM_IN_Y_PIXEL)
        pidRect.setWidth(math.ceil(self._pidSelection.width()/xScaled) + 2 * ZOOM_IN_X_PIXEL)
        pidRect.setHeight(math.ceil(self._pidSelection.height()/yScaled) + 2 * ZOOM_IN_Y_PIXEL)
        preRect = QRect()
        preRect.setX(ox + math.floor(self._preSelection.x()/xScaled))
        preRect.setY(oy + math.floor(self._preSelection.y()/yScaled))
        preRect.setWidth(math.ceil(self._preSelection.width()/xScaled))
        preRect.setHeight(math.ceil(self._preSelection.height()/yScaled))
        screenRect = QApplication.desktop().availableGeometry(QPoint(self._x, self._y))
        bigRect = QRect(screenRect.x(), self._y-self._h/2, screenRect.width(), self._h)
        # bigRect = QRect(self._x-self._w/2, self._y-self._h/2, self._w, self._h)
        return preRect, pidRect, bigRect

    def resetRubberBand(self):
        self._preSelection = QtCore.QRect(0, 0, 0, 0)
        self._pidSelection = QtCore.QRect(0, 0, 0, 0)
        self._preSelectionBeforeDrag = QtCore.QRect(0, 0, 0, 0)
        self._pidSelectionBeforeDrag = QtCore.QRect(0, 0, 0, 0)
        self.resizingFrom = MOUSE_OUT
        self.selRectStart = QtCore.QPoint(0, 0)
        self.selRectEnd = QtCore.QPoint(0, 0)
        self.rbDistX = 0
        self.rbDistY = 0
        self.drawingRubberBand = self.movingRubberBand = self.resizingRubberBand = False
        self.startedDrawingRubberBand = False

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

    def drawRubberband(self, painter, rect, color, lineSize):
        painter.save()
        pen = QPen(color, lineSize, Qt.SolidLine, Qt.SquareCap)
        painter.setPen(pen)
        offset = -(lineSize / 2)
        if rect.width() > 0 and rect.height() > 0:
            drawRect = QRectF(rect)
            drawRect.setSize(QSizeF(rect.size().width() - offset, rect.size().height() - offset))
            drawRect.setX(drawRect.x() + offset)
            drawRect.setY(drawRect.y() + offset)
            painter.drawRect(drawRect)
        painter.restore()

    def showEvent(self, e):
        self.raise_()
        self.repaint()
        self.activateWindow()

    def paintEvent(self, e):
        painter = QPainter(self)
        painter.drawPixmap(0, 0, self._pixmap.scaled(self.size()))
        self.drawRubberband(painter, self._pidSelection, QColor(227, 65, 51), 1)
        self.drawRubberband(painter, self._preSelection, QColor(255, 153, 0), 1)

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
            self.setCursor(CLOSED_HAND_SHAPE)
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
        self.selectionChanged.emit()

    def mouseMoveEvent(self, event):
        # Check if the mouse is over the rubber band
        mousePos = event.pos()
        if self.checkMouseOverRubberBand(mousePos) == MOUSE_OVER_INSIDE:
            # Mouse is over rubber band
            if not self.drawingRubberBand and not self.movingRubberBand and not self.resizingRubberBand:
                self.setCursor(OPEN_HAND_SHAPE)
            elif self.movingRubberBand:
                self.setCursor(CLOSED_HAND_SHAPE)
        # If the mouse is on the left side of the rubberband
        elif not self.movingRubberBand and not self.drawingRubberBand and (self.checkMouseOverRubberBand(mousePos) == MOUSE_OVER_LEFT or self.checkMouseOverRubberBand(mousePos) == MOUSE_OVER_RIGHT):
            self.setCursor(HORIZONTAL_SHAPE)
        elif not self.movingRubberBand and not self.drawingRubberBand and (self.checkMouseOverRubberBand(mousePos) == MOUSE_OVER_TOP or self.checkMouseOverRubberBand(mousePos) == MOUSE_OVER_BOTTOM):
            self.setCursor(VERTICAL_SHAPE)
        elif not self.movingRubberBand and not self.drawingRubberBand and (self.checkMouseOverRubberBand(mousePos) == MOUSE_OVER_TOPLEFT or self.checkMouseOverRubberBand(mousePos) == MOUSE_OVER_BOTTOMRIGHT):
            self.setCursor(LEFT_DIAGONAL_SHAPE)
        elif not self.movingRubberBand and not self.drawingRubberBand and (self.checkMouseOverRubberBand(mousePos) == MOUSE_OVER_TOPRIGHT or self.checkMouseOverRubberBand(mousePos) == MOUSE_OVER_BOTTOMLEFT):
            self.setCursor(RIGHT_DIAGONAL_SHAPE)
        elif not self.movingRubberBand and not self.resizingRubberBand:
            self.setCursor(CROSS_SHAPE)
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
