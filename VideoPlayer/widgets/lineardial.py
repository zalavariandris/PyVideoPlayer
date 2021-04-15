from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

class LinearDial(QDial):
    def __init_(self, parent=None):
        super().__init_(parent=parent)
        self.lastValue = None
        self.lastPos = None

    def mousePressEvent(self, event):
        self.lastValue = self.value()
        self.lastPos = event.pos()

    def mouseMoveEvent(self, event):
        delta = event.pos()-self.lastPos
        self.setValue(self.lastValue+(delta.x()-delta.y())/10 )

    def mouseReleaseEvent(self, event):
        delta = event.pos()-self.lastPos
        self.setValue(self.lastValue+(delta.x()-delta.y())/10 )