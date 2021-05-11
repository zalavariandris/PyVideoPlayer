from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

import numpy as np

class Oscilloscope(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self._values = []   # an array to hold all the values
        self._minimum = 0   # lowest value
        self._maximum = 100 # highest value
        self._count = None  # number of plots
        self._length = 0

    def push(self, *values):
        if self._count == None:
            self._count = len(values)

        assert len(values) == self._count, "{}!={}".format( len(values), self._count)
        while len(self._values)>100:
            self._values.pop(0)

        self._values.append(values)
        self._length+=1
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

    # def average(self):
    #     if not self._values:
    #         return 0
    #     total = 0
    #     for val in self._values:
    #         total+=val
    #     return total / len(self._values)

    def paintEvent(self, event):
        painter = QPainter(self)

        painter.setPen(Qt.NoPen)
        painter.setBrush(self.palette().base().color())
        painter.drawRoundedRect(QRect(0, 0, self.width(), self.height()), 4,4)

        if self._count is None:
            return
        if not self._length>0:
            return

        colors = [QColor.fromHslF(i/self._count, 0.8, 0.5, 0.5) for i in range(self._count)]

        for j in range(self._count):
            path = QPainterPath()
            path.moveTo(0,self.height())

            for i, value_stack in enumerate(self._values):
                value = value_stack[j]
                x = i/100*self.width()
                y = value / (self._maximum-self._minimum) * self.height() + self._minimum
                y = self.height()-y
                path.lineTo(x, y)

            path.lineTo(i/100*self.width(), self.height())

            pen = QPen(self.palette().color(QPalette.Disabled, QPalette.Text))
            pen.setWidth(1.0)
            painter.setPen(Qt.NoPen)
            painter.setBrush(colors[j])

            painter.drawPath(path)

            # pen = QPen(self.palette().color(QPalette.Text))
            # painter.setPen(pen)
            # metrics = painter.fontMetrics()
            # text = "{:.0f}".format(self.average())
            # painter.drawText(QRect(self.width()/2-metrics.size(Qt.TextSingleLine, text).width()/2, self.height()/2-metrics.capHeight(), self.width(), self.height()), text)

            # painter.end()

        # painter.end(()

    def sizeHint(self):
        return QSize(100, 22)

    # def minimumSizeHint(self):
    #     return QSize(10, 6)

    # def maximumSizeHint(sekf):
    #     return QSize(100,6)


def main():
    import numpy as np
    app = QApplication.instance() or QApplication()
    osc = Oscilloscope()
    timer = QTimer()
    i=0
    @timer.timeout.connect
    def _():
        osc.push(np.random.rand()*10, np.random.rand()*20, np.random.rand()*30, np.random.rand()*40)
    timer.start(1000/60)
    osc.show()
    app.exec_()

if __name__ == "__main__":
    main()
