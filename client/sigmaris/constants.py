'''const value'''
from PyQt5 import QtCore

_translate = QtCore.QCoreApplication.translate

MOUSE_OVER_LEFT = 0x0
MOUSE_OVER_RIGHT = 0x1
MOUSE_OVER_TOP = 0x2
MOUSE_OVER_BOTTOM = 0x3
MOUSE_OVER_INSIDE = 0x4
MOUSE_OVER_TOPLEFT = 0x5
MOUSE_OVER_TOPRIGHT = 0x6
MOUSE_OVER_BOTTOMLEFT = 0x7
MOUSE_OVER_BOTTOMRIGHT = 0x8
MOUSE_OUT = 0x9

CROSS_SHAPE = QtCore.Qt.CrossCursor
OPEN_HAND_SHAPE = QtCore.Qt.OpenHandCursor
CLOSED_HAND_SHAPE = QtCore.Qt.ClosedHandCursor
VERTICAL_SHAPE = QtCore.Qt.SizeVerCursor
HORIZONTAL_SHAPE = QtCore.Qt.SizeHorCursor
LEFT_DIAGONAL_SHAPE = QtCore.Qt.SizeFDiagCursor
RIGHT_DIAGONAL_SHAPE = QtCore.Qt.SizeBDiagCursor


DETECTIONS = {
    'lung_nodule_det', _translate('12sigma.detection', 'lung_nodule_det'),
    'lung_dr_det', _translate('12sigma.detection', 'lung_dr_det'),
    'mammo_det', _translate('12sigma.detection', 'mammo_det'),
    'brain_det', _translate('12sigma.detection', 'brain_det'),
    'liver_det', _translate('12sigma.detection', 'liver_det'),
}

FAILED_STRING = "failed"
WAITING_STRING = "waiting"
RUNNING_STRING = "running"
SUCCEED_STRING = "succeed"
COMPUTED_STRING = "computed"
PUSHING_STRING = "pushing"
HANGED_STRING = "hanged"
UNKNOWN_STRING = "unknown"

DEFAULT_VALUE = -1
WAITING_VALUE = 0
RUNNING_VALUE = 1
HEALTH_VALUE = 2
DISEASE_VALUE = 3
FAILED_VALUE = 4
