
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QPixmap
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTableWidget, QLabel, QHeaderView, QAbstractItemView, QTableWidgetItem
from sigmaris.utils import loadUI


class HandBookWidget(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self._initUI()

    def _initUI(self):
        self.verticalLayout = QVBoxLayout(self)
        self.verticalLayout.setContentsMargins(20, 20, 20, 15)
        self.verticalLayout.setSpacing(20)
        self.introLabel = QLabel(self)
        self.verticalLayout.addWidget(self.introLabel)
        self.statusTable = QTableWidget(self)
        self.statusTable.setColumnCount(2)
        self.statusTable.setRowCount(6)
        self.verticalLayout.addWidget(self.statusTable)
        self.setWindowTitle('SigmaBuoy使用指南')
        self.introLabel.setText(
            "SigmaBuoy是图玛深维开发的一款自动识别及跳转工具, 它有以下状态：")
        self.introLabel.setFont(QFont('Arial', 11, 50))
        self.introLabel.setWordWrap(True)
        self.setFixedSize(850, 480)
        self.statusTable.setColumnWidth(0, 200)
        header = ['展示形态', '含义']
        self.statusTable.setHorizontalHeaderLabels(header)
        self.statusTable.horizontalHeader().setStyleSheet(
            "QHeaderView::section {background-color:rgb(157, 195, 230);color: white; border: 1px solid #6c6c6c; }")
        self.statusTable.horizontalHeader().setFont(QFont('Arial', 14, 75))
        self.statusTable.verticalHeader().hide()
        self.statusTable.horizontalHeader().setStretchLastSection(True)
        self.statusTable.verticalHeader().setDefaultSectionSize(56)
        self.statusTable.horizontalHeader().setMinimumHeight(60)
        self.statusTable.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.statusTable.setSelectionMode(QAbstractItemView.NoSelection)
        self.setImageData()
        self.setMeanData(0, '表示软件初始状态')
        self.setMeanData(1, '表示识别出且已预测出病灶，点击即可查看预测结果')
        self.setMeanData(2, '表示识别出且已预测，但未发现病灶，无需点击')
        self.setMeanData(3, '表示未找到当前影像号')
        self.setMeanData(4, '表示等待计算')
        self.setMeanData(5, '表示计算出错')
        # self.statusTable.resizeRowsToContents()
        # self.statusTable.resizeColumnsToContents()

    def setMeanData(self, row, contents):
        item = QTableWidgetItem(str(contents))
        item.setFont(QFont('Arial', 14, 50))
        item.setTextAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        self.statusTable.setItem(row, 1, item)

    def setImageData(self):
        data = {
            0: ':/demo/default',
            1: ':/demo/disease',
            2: ':/demo/health',
            3: ':/demo/warning',
            4: ':/demo/pending',
            5: ':/demo/error'
        }
        for k, v in data.items():
            tLabel = QLabel()
            tLabel.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
            tLabel.setPixmap(QPixmap(v))
            self.statusTable.setCellWidget(k, 0, tLabel)
