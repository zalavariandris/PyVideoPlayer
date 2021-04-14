from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

class Oscilloscope(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self._values = []
        self._minimum = 0
        self._maximum = 100

    def push(self, value):
        while len(self._values)>100:
            self._values.pop(0)

        self._values.append(value)

        self.update()

    def clear(self):
        self._values = []

    def minimum(self):
        return self._minimum

    def setMinimum(self, value):
        self._minimum = value

    def maximum(self):
        return self._maximum

    def setMaximum(self, value):
        self._maximum = value

    def average(self):
        if not self._values:
            return 0
        total = 0
        for val in self._values:
            total+=val
        return total / len(self._values)

    def paintEvent(self, event):
        painter = QPainter(self)

        painter.setPen(Qt.NoPen)
        painter.setBrush(self.palette().base().color())
        painter.drawRoundedRect(QRect(0, 0, self.width(), self.height()), 4,4)

        path = QPainterPath()
        if self._values:
            path.moveTo(0, self._values[0])

        for i, value in enumerate(self._values[1:]):
            x = i/100*self.width()
            y = value / (self._maximum-self._minimum) * self.height() + self._minimum
            y = self.height()-y
            path.lineTo(x, y)

        pen = QPen(self.palette().color(QPalette.Disabled, QPalette.Text))
        pen.setWidth(1.0)
        painter.setPen(pen)

        painter.drawPath(path)

        pen = QPen(self.palette().color(QPalette.Text))
        painter.setPen(pen)
        metrics = painter.fontMetrics()
        text = "{:.0f}".format(self.average())
        painter.drawText(QRect(self.width()/2-metrics.size(Qt.TextSingleLine, text).width()/2, self.height()/2-metrics.capHeight(), self.width(), self.height()), text)

        painter.end()

        # painter.end(()

    def sizeHint(self):
        return QSize(100, 22)

    # def minimumSizeHint(self):
    #     return QSize(10, 6)

    # def maximumSizeHint(sekf):
    #     return QSize(100,6)
