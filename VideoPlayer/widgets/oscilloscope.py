from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

import numpy as np
import time

from functools import cache

class Oscilloscope(QWidget):
    def __init__(self, legend=[], parent=None):
        super().__init__(parent=parent)
        self._values = None   # an array to hold all the values
        self._minimum = 0   # lowest value
        self._maximum = 1000 # highest value
        self._fixed_minimum = None
        self._fixed_maximum = None
        self._count = None  # number of plots
        self._length = 0

        self.legend = legend
        self.hovered = -1

        self._stack = False

        self.setMouseTracking(True)

    def push(self, *values):
        if self._values is None:
            # self._values = []
            self._values = np.array([values])
        if self._count == None:
            self._count = len(values)

        assert len(values) == self._count, "{}!={}".format( len(values), self._count)
        while len(self._values)>100:
            self._values = self._values[1:]
            # self._values.pop(0)

        self._values = np.append(self._values, [values], axis=0)

        self.minimum.cache_clear()
        self.maximum.cache_clear()
        # self._values.append(values)

        self._length+=1

        if self._length==2:
            arr = np.array(self._values)
            self._minimum = np.min(arr)
            self._maximum = np.max(arr)
        elif self._length>2:
            min_val = min(np.array(values))
            if min_val<self._minimum:
                self._minimum = min_val
            max_val = max(np.array(values))
            if max_val>self._maximum:
                self._maximum = max_val

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
            i/100*self.width(),
            self.height() - val / (self.maximum()-self.minimum()) * self.height() - self.minimum()
        )

    def shapes(self):
        if not self._count:
            return []

        self._stack = True
        for j in range(self._count):
            
            # create vertices
            points = []
            
            if j>0 and self._stack:
                for i in reversed(range(len(self._values))):
                    points.append(self.mapToScene(i, sum(self._values[i][:j])))
            else:
                # bottom right
                points.append(self.mapToScene(self._length, self.minimum()))

                # bottom left
                points.append(self.mapToScene(0, self.minimum()))

            for i in range(len(self._values)):
                val = self._values[i][j]
                if self._stack and j>0:
                    val+=sum(self._values[i][:j])
                # map to scene
                points.append(self.mapToScene(i, val))

            # create path
            path = QPainterPath()
            path.moveTo( points[0] )
            for point in points:
                path.lineTo(point)

            yield path

    def paintEvent(self, event):
        painter = QPainter(self)

        """Paint Background"""
        painter.setPen(Qt.NoPen)
        painter.setBrush(self.palette().base().color())
        painter.drawRoundedRect(QRect(0, 0, self.width(), self.height()), 4,4)

        """Guards"""
        if self._count is None:
            return
        if not self._length>1:
            return

        """Create Colors"""
        colors = [QColor.fromHslF(i/self._count, 0.8, 0.5, 0.5) for i in range(self._count)]

        """Paint Shapes"""
        # begin = time.time()
        shapes = [shape for shape in self.shapes()]
        
        for i in range(len(shapes)):
            shape = shapes[i]
            color = colors[i]
            # pen = QPen(self.palette().color(QPalette.Disabled, QPalette.Text))
            # pen.setWidth(1.0)
            # painter.setPen(Qt.NoPen)
            painter.setBrush(color.lighter() if i==self.hovered else color)
            painter.drawPath(shape)

        if self.hovered>=0:
            pen = QPen(self.palette().color(QPalette.Text))
            painter.setPen(pen)
            value = self._values[self.hovered][-1]
            try:
                text = "{}({:.3f})".format(self.legend[self.hovered], np.average(self._values[:][self.hovered]))
            except IndexError:
                text = "{}({:.3f})".format(self.hovered, np.average(self._values[:][self.hovered]))
            pos = self.mapFromGlobal(QCursor.pos())
            painter.drawText(pos.x(), pos.y(), text)

        # """Paint strokes"""
        # # print(self._values.shape)
        # for shape_idx in range(self._values.shape[1]):
        #     path = QPainterPath()
        #     path.moveTo(self.mapToScene(0, self._minimum))
        #     for i in range(1, self._values.shape[0]):
        #         path.lineTo(self.mapToScene(i, self._values[i][shape_idx]))

        #     pen = QPen(self.palette().color(QPalette.Text))
        #     painter.setPen(pen)
        #     painter.setBrush(Qt.NoBrush)
        #     painter.drawPath(path)
        #     # print(shape_idx)

        # dt = time.time()-begin
        # print("shapes:", 1/dt if dt>0 else 0)


    def sizeHint(self):
        return QSize(100, 22)

    def mouseMoveEvent(self, event):
        self.hovered = -1
        for i, shape in reversed([(i, shape) for i, shape in enumerate(self.shapes())]):
            if shape.contains(event.pos()):
                self.hovered = i
                break
        self.update()

    def minimumSizeHint(self):
        return QSize(10, 6)

    def maximumSizeHint(sekf):
        return QSize(100,6)

    def leaveEvent(self, event):
        self.hovered = -1
        print("LEAVE")
        self.update()


def main():
    import numpy as np
    import math
    import time

    app = QApplication.instance() or QApplication()
    osc = Oscilloscope()
    # osc.setMaximum(5)
    timer = QTimer()
    i=0
    @timer.timeout.connect
    def _():
        val1 = math.cos(time.time())+1
        val2 = math.cos(time.time()*20)*0.3+0.3
        val3 = math.cos(time.time()*5)+1
        osc.push(val1, val2, val3)
        # print("range {:.2f} {:.2f}".format(osc.minimum(), osc.maximum()))
    timer.start(1000/60)
    osc.show()
    app.exec_()

if __name__ == "__main__":
    main()
