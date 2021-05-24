from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

import numpy as np
import time

from functools import cache

class Oscilloscope(QWidget):
    def __init__(self, legend=[], parent=None, format="{name}: {value:.2f}"):
        super().__init__(parent=parent)
        self._values = None   # an array to hold all the values
        self._fixed_minimum = None
        self._fixed_maximum = None
        self._samples_count = 100
        # self._count = None  # number of plots

        self.legend = legend
        self.hovered = -1

        self._stack = False

        self.setMouseTracking(True)

        self.format = format

    def push(self, *values):
        if self._values is None:
            self._values = np.array([values])

        while self._values.shape[0]>self._samples_count:
            self._values = self._values[1:]

        self._values = np.append(self._values, [values], axis=0)

        self.minimum.cache_clear()
        self.maximum.cache_clear()

        self.update()

    def clear(self):
        self._values = None

    @cache
    def minimum(self):
        if self._fixed_minimum is not None:
            return self._fixed_minimum
        return np.min(self._values)
        # return self._minimum

    def setMinimum(self, value):
        self._fixed_minimum = value

    @cache
    def maximum(self):
        if self._fixed_maximum is not None:
            return self._fixed_maximum
        return np.max(np.sum(self._values, axis=1) if self._stack else self._values)
        # return self._maximum

    def setMaximum(self, value):
        self._fixed_maximum = value

    def mapToScene(self, i, val):
        return QPointF(
            i/self._samples_count*self.width(),
            self.height() - val / (self.maximum()-self.minimum()) * self.height() - self.minimum()
        )

    def shapes(self):
        if not self._values.shape[1]:
            return []

        for shape_idx in range(self._values.shape[1]):
            
            # create vertices
            points = []
            
            if shape_idx>0 and self._stack:
                for i in reversed(range(self._values.shape[0])):
                    points.append(self.mapToScene(i, sum(self._values[i][:shape_idx])))
            else:
                # bottom right
                length = self._values.shape[0]
                points.append(self.mapToScene(length, self.minimum()))

                # bottom left
                points.append(self.mapToScene(0, self.minimum()))

            for i in range(len(self._values)):
                if self._stack and shape_idx>0:
                    val = sum(self._values[i][:shape_idx+1])
                else:
                    val = self._values[i][shape_idx]
                # map to scene
                points.append(self.mapToScene(i, val))

            # create path
            path = QPainterPath()
            path.moveTo( points[0] )
            for point in points:
                path.lineTo(point)

            yield path

    def paint_strokes(self, painter):
        for shape_idx in range(self._values.shape[1]):
            points = []
            for i in range(0, self._values.shape[0]):
                val = np.sum(self._values[i][:shape_idx+1]) if self._stack else self._values[i][shape_idx]
                points.append(self.mapToScene(i, val))

            path = QPainterPath()
            path.moveTo(points[0])
            for point in points[1:]:
                path.lineTo(point)

            lineColor = self.palette().color(QPalette.Text)
            lineColor.setAlphaF(0.25)
            pen = QPen(lineColor)
            pen.setWidth(0)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawPath(path)

    def paintEvent(self, event):
        painter = QPainter(self)

        """Paint Background"""
        painter.setPen(Qt.NoPen)
        painter.setBrush(self.palette().base().color())
        painter.drawRoundedRect(QRect(0, 0, self.width(), self.height()), 4,4)

        """Guards"""
        if self._values is None or not self._values.shape[1] > 0:
            return

        if not self._values.shape[0]>1:
            return

        """Create Colors"""
        colors = [QColor.fromHslF(i/self._values.shape[1], 0.8, 0.5, 0.5) for i in range(self._values.shape[1])]

        # """Paint Shapes"""
        # # begin = time.time()
        shapes = [shape for shape in self.shapes()]
        
        for i, (shape, color) in enumerate(zip(shapes, colors)):
            painter.setBrush(color.lighter() if i==self.hovered else color)
            painter.drawPath(shape)

        """Paint Label"""
        if self.hovered>=0:
            pen = QPen(self.palette().color(QPalette.Text))
            painter.setPen(pen)
            value = self._values[-1][self.hovered]
            try:
                text = self.format.format(name=self.legend[self.hovered], value=self._values[-1][self.hovered])
            except IndexError:
                text = self.format.format(name=self.hovered, value=self._values[-1][self.hovered])
            pos = self.mapFromGlobal(QCursor.pos())
            painter.drawText(pos.x(), pos.y(), text)

        """Paint strokes"""
        # self.paint_strokes(painter)

        # dt = time.time()-begin
        # print("shapes:", 1/dt if dt>0 else 0)

    def sizeHint(self):
        return QSize(100, 22)

    def mouseMoveEvent(self, event):
        self.hovered = -1
        for i, shape in [(i, shape) for i, shape in enumerate(self.shapes())]:
            if shape.contains(event.pos()):
                self.hovered = i
                break
        self.update()

    def minimumSizeHint(self):
        return QSize(10, 6)

    def maximumSizeHint(sekf):
        return QSize(100, 6)

    def leaveEvent(self, event):
        self.hovered = -1
        self.update()


def main():
    import numpy as np
    import math
    import time

    app = QApplication.instance() or QApplication()
    osc = Oscilloscope()
    osc._stack = True
    # osc.setMaximum(5)

    times = {}



    timer = QTimer()
    i=0
    @timer.timeout.connect
    def _():
        val1 = math.cos(time.time())+1
        val2 = math.cos(time.time()*20)*0.3+0.3
        val3 = math.cos(time.time()*5)+1
    osc.push(0.1, 0.3, 1.0)
    osc.push(0.2, 0.4, 1.1)
    osc.push(0.2, 0.4, 1.1)
    osc.push(0.2, 0.4, 1.1)
    osc.push(0.2, 0.4, 1.1)
    osc.push(2.2, 2.4, 2.1)
        # print("range {:.2f} {:.2f}".format(osc.minimum(), osc.maximum()))
    timer.start(1000/60)
    osc.show()
    app.exec_()

if __name__ == "__main__":
    main()
