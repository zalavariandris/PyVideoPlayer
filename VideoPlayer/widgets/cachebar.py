from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

class CacheBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self._values = [1,2,3,4,5,10,20]
        self._start = 0
        self._end = 100

    def paintEvent(self, event):
        padding = 8
        tick_width = self.width() / (self._end-self._start)
        tick_width/=1.0

        # draw
        painter = QPainter(self)

        # draw ticks
        tick_color = self.palette().highlight().color()
        painter.setPen(QPen(tick_color, 1.0))
        # painter.setBrush(tick_color)

        for pos in self._values:
            x = pos-self._start
            x/=self._end-self._start
            x*=self.width()-padding*2
            x+=padding
            # painter.drawRect(x,0,tick_width, self.height())
            painter.drawLine(x, 0, x, self.height())

        # draw background rect
        # if self.height()>=3:
        #     painter.setPen(QPen(Qt.black))
        #     painter.drawRect(padding,0,self.width()-padding*2, self.height())

        painter.end()

    def setValues(self, values):
        self._values = values
        self.update()

    def values(self):
        return self._values

    def setRange(self, start, end):
        print("range", start, end)
        self._start = start
        self._end = end

    def range(self):
        return (self._start, self._end)

    def sizeHint(self):
        return QSize(400, 10)

    def minimumSizeHint(self):
        return QSize(10, 3)