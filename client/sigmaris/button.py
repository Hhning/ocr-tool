from PyQt5 import QtCore, QtGui, QtWidgets


class ExButton(QtWidgets.QPushButton):

    def __init__(self, parent=None):
        super().__init__(parent)
        self._menu = None
        # self.setContextMenuPolicy(QtCore.Qt.DefaultContextMenu)

    def registerMenu(self, menu):
        self._menu = menu

    def contextMenuEvent(self, event):
        if self._menu:
            self._menu.exec_(QtGui.QCursor.pos())
        else:
            super().contextMenuEvent(event)
