import cv2
import numpy as np
from PyQt5.QtCore import QBuffer
from PyQt5.QtGui import QImage


def nparray2qimage(array):
    height, width, channel = array.shape
    assert channel == 3 or channel == 4
    fmt = QImage.Format_RGB888 if channel == 3 else QImage.Format_RGB32
    image = QImage(array.flatten(), width, height, fmt)
    return image


def qimage2nparray(image):
    width = image.width()
    height = image.height()
    depth = image.depth()
    ptr = image.constBits()
    ptr.setsize(image.byteCount())
    arrary = np.array(ptr).reshape(height, width, depth//8)
    return arrary


def qimage2bytearray(image):
    buffer = QBuffer()
    buffer.open(QBuffer.ReadWrite)
    image.save(buffer, 'png')
    return buffer.data()


def nparray2bytearray(array):
    image = nparray2qimage(array)
    return qimage2bytearray(image)


def imread(image):
    if isinstance(image, str):
        return cv2.imread(image)
    else:
        return qimage2nparray(image)


def templateMatching(img_name, template_name, setting):
    img = imread(img_name) #读大图
    img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    img_template = cv2.imread(template_name, 0) #读"影像号"图
    w, h = img_template.shape[::-1]
    res = cv2.matchTemplate(img_gray, img_template, cv2.TM_CCOEFF_NORMED) # matching
    threshold = 0.85
    loc = np.where(res >= threshold)
    if len(loc[0]) <= 0:
        return
    x = loc[1][0] + setting['dx']
    y = loc[0][0] + setting['dy']
    crop_img = img[y:y+setting['dh'], x:x+setting['dw']]
    return crop_img
