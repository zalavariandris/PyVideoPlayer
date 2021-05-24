from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

def get_ranges(data):
    result = []
    if not data:
        return result
    idata = iter(sorted([int(v) for v in data]))
    first = prev = next(idata)
    for following in idata:
        if following - prev == 1:
            prev = following
        else:
            result.append((first, prev + 1))
            first = prev = following
    # There was either exactly 1 element and the loop never ran,
    # or the loop just normally ended and we need to account
    # for the last remaining range.
    result.append((first, prev+1))
    return result

class CacheBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self._values = [1,2,3,4,5,10,11,12, 20]
        self._minimum = 0
        self._maximum = 99

    def minimum(self):
        return self._minimum

    def maximum(self):
        return self._maximum

    def paintEvent(self, event):
        # padding = 0
        # tick_width = self.width() / (self._maximum-self._minimum)
        # tick_width/=1.0

        # draw
        painter = QPainter(self)

        # draw ticks
        tick_color = self.palette().highlight().color()
        
        # painter.setBrush(tick_color)

        ranges = [r for r in get_ranges(self._values)]
        # print(ranges)

        def to_pos(val):
            val-=self.minimum()
            val/=self.maximum()-self.minimum()+1
            val*=self.width()
            return val

        painter.setPen(Qt.NoPen)
        painter.setBrush(tick_color)

        for r in ranges:
            start = r[0]
            end = r[1]
            x = to_pos(start)
            w = to_pos(end)-x
            painter.drawRect(x,0,w,self.height())

        painter.setPen(QPen(tick_color, 1.0))
        # for pos in self._values:
        #     x = get_x(pos)
        #     # painter.drawRect(x,0,tick_width, self.height())
        #     painter.drawLine(x, 0, x, self.height())

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

    def setRange(self, minimum, maximum):
        print("range", minimum, maximum)
        self._minimum = minimum
        self._maximum = maximum
        self.update()

    def range(self):
        return (self._minimum, self._maximum)

    def sizeHint(self):
        return QSize(400, 10)

    def minimumSizeHint(self):
        return QSize(10, 3)