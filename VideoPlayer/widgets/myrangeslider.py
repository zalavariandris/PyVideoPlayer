from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

class Thumb(QPushButton):
    # def mouseMoveEvent(self, event):
    #     super().mouseMoveEvent(event)
    #     event.ignore()

    def sizeHint(self):
        return QSize(8, 22)

    # def mousePressEvent(self, event):
    #     event.ignore()

    # def paintEvent(self, event):
    #     pass

class MyRangeSlider(QWidget):
    valuesChanged = Signal(int, int)
    rangeChanged = Signal(int, int)
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self._range = (0, 99)
        self._values = (10, 80)

        self.span = Thumb(self)
        # self.span.setFlat(True)

        self.left_thumb = Thumb(self)
        # self.left_thumb.setFlat(True)
        self.left_thumb.setCursor(Qt.SizeHorCursor)

        self.right_thumb = Thumb(self)
        # self.right_thumb.setFlat(True)
        self.right_thumb.setCursor(Qt.SizeHorCursor)

        self.span.installEventFilter(self)
        self.left_thumb.installEventFilter(self)
        self.right_thumb.installEventFilter(self)

    def updateElements(self):
        x1 = self._to_pos(self.values()[0])
        x11 = self._to_pos(self.values()[0]+1)
        tick_width = x11-x1

        left = self._to_pos(self.values()[0])
        right = self._to_pos(self.values()[1]+1)

        self.left_thumb.setFixedHeight(self.height())
        # self.left_thumb.setFixedWidth(tick_width)
        self.left_thumb.move(left-self.left_thumb.width()/2, 0)
        self.right_thumb.setFixedHeight(self.height())
        # self.right_thumb.setFixedWidth(tick_width)
        self.right_thumb.move(right-self.right_thumb.width()/2, 0)

        if right-left<=0:
            if self.span.isVisible():
                self.span.hide()
        else:
            if not self.span.isVisible():
                self.span.show()

            self.span.setFixedHeight(self.height())
            self.span.move(left, 0)
            self.span.setFixedWidth(right-left)

    def _to_pos(self, val):
        val = int(val)
        val-=self.minimum()
        val/=self.maximum()-self.minimum()+1
        val*=self.width()
        return val

    def _to_value(self, x):
        x/=self.width()
        x*=self.maximum()-self.minimum()+1
        x+=self.minimum()
        return int(x)

    def showEvent(self, event):
        self.updateElements()
        self.update()

    def resizeEvent(self, event):
        self.updateElements()
        self.update()

    def values(self):
        return self._values

    def setValues(self, v1=None, v2=None):
        if not v1<=v2:
            return
        self._values = (v1, v2)
        self.valuesChanged.emit(v1, v2)

        self.update()
        self.updateElements()

    def minimum(self):
        return self._range[0]

    def setMinimum(self, val):
        self._range = (val, self._range[1])
        self.rangeChanged.emit(val, self._range[1])
        self.updateElements()
        self.update()

    def maximum(self):
        return self._range[1]

    def setMaximum(self, val):
        self._range = (self._range[0], val)
        self.rangeChanged.emit(self._range[0], val)
        self.updateElements()
        self.update()

    def reset(self):
        self.setValues(self.minimum(), self.maximum())

    def mouseDoubleClickEvent(self, event):
        self.reset()

    # def paintEvent(self, event):
    #     backgroundColor = self.palette().base().color()
    
    #     painter = QPainter(self)
    #     painter.setPen(Qt.NoPen)
    #     painter.setBrush(backgroundColor)
    #     painter.drawRect(event.rect())

    #     # self.paintThumb(painter, self.values()[0])
    #     # self.paintThumb(painter, self.values()[1])

    #     x1 = self._to_pos(self.values()[0])
    #     x2 = self._to_pos(self.values()[1]+1)
    #     painter.setBrush(QColor(100,100,100,100))
    #     painter.drawRect(x1, 0, x2-x1, self.height())

    # def paintThumb(self, painter, val):
    #     thumbColor = self.palette().button().color()

    #     painter.setBrush(thumbColor)
    #     painter.drawRect(self._to_pos(val)-11, 0, 22, self.height())


    # def mousePressEvent(self, event):
    #     self._lastpos = event.pos()
    #     self._lastvalues = self.values()

    def eventFilter(self, obj, event):
        # print(event.type())
        # print(obj, self.left_thumb)

        if event.type() == QEvent.MouseButtonDblClick:
            self.reset()
            return True

        delta = QPoint()
        if event.type() == QEvent.MouseButtonPress:
            self._lastpos = event.screenPos()
            self._lastvalues = self.values()
            return True

        if event.type() == QEvent.MouseMove:
            delta = event.screenPos()-self._lastpos
            # print(delta)
            delta_value = self._to_value(event.screenPos().x()) - self._to_value(self._lastpos.x())
            # print(delta_value)

            if obj is self.span:
                self.setValues(self._lastvalues[0]+delta_value, self._lastvalues[1]+delta_value)


            if obj is self.left_thumb:
                v1 = self._lastvalues[0]+delta_value
                v2 = self.values()[1]

                if v1>v2:
                    v1=v2

                self.setValues(v1, v2)


            if obj is self.right_thumb:
                v1 = self.values()[0]
                v2 = self._lastvalues[1]+delta_value
                if v2<v1:
                    v2=v1
                self.setValues(v1, v2)

            return True


            if event.type() == QEvent.MouseButtonRelease:
                return True

        return False

    # def mouseMoveEvent(self, event):
    #     if self.left_thumb.isDown():
    #         v1 = self._to_value(event.x())

    #         if v1<self.minimum():
    #             v1 = self.minimum()
    #         if v1>self.values()[1]:
    #             v1 = self.values()[1]

    #         self.setValues(v1, self.values()[1])

    #     if self.right_thumb.isDown():
    #         v2 = self._to_value(event.x())
    #         if v2>self.maximum():
    #             v2 = self.maximum()
    #         if v2<self.values()[0]:
    #             v2 = self.values()[0]

    #         self.setValues(self.values()[0], v2)

    #     # if self.span.isDown():
    #     #     delta = event.pos()-self._lastpos
    #     #     v1 = self._to_value(self._lastvalue[0]+delta.x())
    #     #     v2 = self._to_value(self._lastvalue[1]+delta.x())
    #     #     self.setValues(v1, v2)

    #     self.updateElements()
    #     self.update()

    def mouseReleaseEvent(self, event):
        pass

if __name__ == "__main__":
    app = QApplication().instance() or QApplication()
    w = MyRangeSlider()
    w.resize(500, 100)
    w.setMaximum(200)
    w.setMinimum(100)
    w.setValues(120, 180)

    @w.valuesChanged.connect
    def _(v1, v2):
        print("values changed", v1, v2)
    w.show()
    app.exec_()