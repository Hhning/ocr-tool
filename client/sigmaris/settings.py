import os
import sys
import copy
import logging
from functools import partial

from PyQt5 import QtWidgets, QtCore, QtGui

from sigmaris.utils import loadUI
from sigmaris.config import appConfig, ROI_PATH
from sigmaris.magnifier import Magnifier
from sigmaris.bbox import BBoxDialog

_logger = logging.getLogger(__name__)
_translate = QtCore.QCoreApplication.translate

_ver = sys.getwindowsversion().major
XP = True if int(_ver) < 6 else False
CITRIXKEY = 'CitrixXP' if XP else 'Citrix'


class RectModel(QtCore.QAbstractTableModel):

    HEADERS = ['X', 'Y', 'W', 'H']

    def __init__(self, parent=None):
        super().__init__(parent)
        self.initData()
    
    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        if role == QtCore.Qt.DisplayRole and orientation == QtCore.Qt.Horizontal:
            return self.HEADERS[section]
        elif role == QtCore.Qt.FontRole:
            font = QtGui.QFont()
            font.setBold(True)
            return font
        else:
            return super().headerData(section, orientation, role)

    def columnCount(self, parent=QtCore.QModelIndex()):
        return 4
    
    def rowCount(self, parent=QtCore.QModelIndex()):
        return len(self.rects)

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if not index.isValid():
            return
        if role == QtCore.Qt.DisplayRole or role == QtCore.Qt.EditRole:
            return self.rects[index.row()].get(self.HEADERS[index.column()].lower(), 0)
        elif role == QtCore.Qt.TextAlignmentRole:
            return QtCore.Qt.AlignCenter

    def setData(self, index, value, role=QtCore.Qt.EditRole):
        if not index.isValid():
            return False
        if role == QtCore.Qt.EditRole:
            try:
                _value = int(float(value))
            except:
                return False
            else:
                self.rects[index.row()][self.HEADERS[index.column()].lower()] = _value
                return True
        return False

    def flags(self, index):
        if not index.isValid():
            return
        flags = QtCore.QAbstractTableModel.flags(self, index)
        flags |= QtCore.Qt.ItemIsEditable
        return flags
    
    def initData(self):
        self.rects = copy.deepcopy(appConfig['OCR']['automatic'].get('rect', []))

    def append(self, item):
        '''添加一行数据，返回labelId'''
        row = self.rowCount()
        self.beginInsertRows(self.parent() or QtCore.QModelIndex(), row, row)
        self.rects.append(item)
        self.endInsertRows()

    def remove(self, row):
        self.beginRemoveRows(self.parent() or QtCore.QModelIndex(), row, row)
        item = self.rects.pop(row)
        self.endRemoveRows()
        return item

    def update(self, row, item):
        self.rects[row] = item
        self.dataChanged.emit(self.index(row, 0), self.index(row, 3))


class SettingsDialog(QtWidgets.QDialog):

    settingsSaved = QtCore.pyqtSignal()
    settingsClosed = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = loadUI(':/12sigma/settings', self)
        self.ui.manBox.toggled.connect(lambda on: self.ui.autoBox.setChecked(not on))
        self.ui.autoBox.toggled.connect(lambda on: self.ui.manBox.setChecked(not on))
        self.ui.addBtn.clicked.connect(self.onAddRect)
        self.ui.delBtn.clicked.connect(self.onDeleteRect)
        self.ui.rectView.horizontalHeader().setSectionsClickable(False)
        self.ui.rectView.horizontalHeader().setFixedHeight(30)
        self.ui.rectView.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        self.ui.urlEditor.editingFinished.connect(self.syncServer)
        self.ui.localRadio.toggled.connect(partial(self.updatePath, 'Local'))
        self.ui.islpRadio.toggled.connect(partial(self.updatePath, 'ISLP'))
        self.ui.citrixRadio.toggled.connect(partial(self.updatePath, CITRIXKEY))
        self.ui.webRadio.toggled.connect(partial(self.updatePath, 'Web'))
        self.rectModel = RectModel()
        self.ui.rectView.setModel(self.rectModel)
        self.updateRow = -1
        candidate = ['patient_id', 'study_id', 'series_id', 'accession_number']
        completer = QtWidgets.QCompleter(candidate, self)
        self.ui.kwEditor.clear()
        self.ui.kwEditor.addItems(candidate)
        self.ui.kwEditor.setCompleter(completer)
        self._magnifier = Magnifier(self)
        self._magnifier.centerDone.connect(self.centerDone)
        self._bbox = BBoxDialog(self)
        self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowContextHelpButtonHint | QtCore.Qt.WindowStaysOnTopHint)

    def updateUI(self):
        ocr = appConfig['OCR']
        manualMode = ocr.get('manualMode', True)
        self.ui.manBox.setChecked(manualMode)
        self.ui.autoBox.setChecked(not manualMode)
        manual = ocr['manual']
        self.ui.keySequenceEdit.setKeySequence(QtGui.QKeySequence(manual['shortcut']))
        self.ui.waitingEditor.setValue(manual['timeout'])
        automatic = ocr['automatic']
        self.rectModel.initData()
        self.rectModel.modelReset.emit()
        self.ui.rateBox.setValue(automatic['interval'])
        server = appConfig['Server']
        self.ui.urlEditor.setText(server.get('endpoint', ''))
        self.ui.kwEditor.setCurrentText(server.get('keyword', 'patient_id'))
        launcher = appConfig['Launcher']
        options = launcher.get('options')
        if options:
            self.ui.autoOpen.setChecked(options.get('autoOpen', False))
        detections = launcher.get('detections')
        if detections is None:      # if no detections config make lung_nodule_det default
            self.ui.lung_nodule_det.setChecked(True)
        else:   # make sure detection is list
            for index in range(self.ui.partsLayout.count()):
                child = self.ui.partsLayout.itemAt(index).widget()
                child.setChecked(child.objectName() in detections)
        launcherType = launcher.get('type', '')
        if launcherType not in ['Local', 'ISLP', CITRIXKEY, 'Web']:
            launcherType = ''
        self.ui.localRadio.setChecked(launcherType == 'Local')
        self.ui.islpRadio.setChecked(launcherType == 'ISLP')
        self.ui.citrixRadio.setChecked(launcherType == CITRIXKEY)
        self.ui.webRadio.setChecked(launcherType == 'Web')
        self.ui.launcherPath.setText(launcher['path'].get(launcherType, '') if launcherType else '')

    def syncServer(self):
        appConfig['Server']['endpoint'] = self.ui.urlEditor.text()

    def updatePath(self, key, checked):
        if checked:
            self.ui.launcherPath.setText(appConfig['Launcher']['path'].get(key, ''))

    def updateConfig(self):
        appConfig['OCR']['manualMode'] = self.ui.manBox.isChecked()
        appConfig['OCR']['manual']['shortcut'] = self.ui.keySequenceEdit.keySequence().toString()
        appConfig['OCR']['manual']['timeout'] = self.ui.waitingEditor.value()
        appConfig['OCR']['automatic']['rect'] = self.rectModel.rects
        appConfig['OCR']['automatic']['interval'] = self.ui.rateBox.value()
        appConfig['Server']['endpoint'] = self.ui.urlEditor.text()
        appConfig['Server']['keyword'] = self.ui.kwEditor.currentText()
        appConfig['Launcher']['options'] = {'autoOpen': self.ui.autoOpen.isChecked()}
        detections = []
        for index in range(self.ui.partsLayout.count()):
            child = self.ui.partsLayout.itemAt(index).widget()
            if child.isChecked():
                detections.append(child.objectName())
        appConfig['Launcher']['detections'] = detections
        launcherType = ''
        if self.ui.localRadio.isChecked():
            launcherType = 'Local'
        elif self.ui.islpRadio.isChecked():
            launcherType = 'ISLP'
        elif self.ui.citrixRadio.isChecked():
            launcherType = CITRIXKEY
        elif self.ui.webRadio.isChecked():
            launcherType = 'Web'
        appConfig['Launcher']['type'] = launcherType
        appConfig['Launcher']['path'][launcherType] = self.ui.launcherPath.text()
        appConfig.dump()

    def onAddRect(self):
        self._magnifier.show()

    def onDeleteRect(self):
        indexes = self.ui.rectView.selectedIndexes()
        if indexes:
            row = indexes[0].row()
            item = self.rectModel.remove(row)
            if 'fc' in item.keys():
                try:
                    os.remove(os.path.join(ROI_PATH, item['fc']))
                except:
                    pass

    def centerDone(self, pos):
        self._bbox.updatePixmap(pos.x(), pos.y())
        self._bbox.exec_()
        if self._bbox.valid:
            self.rectModel.append(self._bbox.setting)
            if 'fc' in self._bbox.setting.keys():
                self._bbox.saveTemplate(self._bbox.setting['fc'])

    def hideEvent(self, e):
        self._magnifier.hide()

    def accept(self):
        self.updateConfig()
        super().accept()
        self.settingsSaved.emit()
        self.settingsClosed.emit()

    def reject(self):
        super().reject()
        self.settingsClosed.emit()
