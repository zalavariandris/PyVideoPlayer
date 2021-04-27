from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

class MySlider(QAbstractSlider):
    def __init__(self, parent=None, orientation=Qt.Horizontal):
        if orientation!=Qt.Horizontal:
            raise NotImplementedError
        super().__init__(parent=parent, orientation=orientation)
        self.setTracking(True)

        self._is_panning = False

        # self._zoom = self.zoom()

        self.update()

    def mousePressEvent(self, event):
        print("press")
        self._lastpos = event.pos()
        self._lastvalue = self.value()
        self._lastmin = self.minimum()
        self._lastmax = self.maximum()
        if event.modifiers() == Qt.AltModifier or Qt.MiddleButton == event.button():
            self._is_panning = True

        print("press", self._is_panning)
        if self._is_panning:
            pass
        else:
            val = self._to_value(event.pos().x())
            self.setSliderPosition(val)
            if self.hasTracking():
                self.setValue(val)
            self.update()

    def mouseMoveEvent(self, event):
        if self._is_panning:
            delta = self._lastpos-event.pos()
            new_min = self._to_value(self._to_pos(self._lastmin)+delta.x())
            new_max = self._to_value(self._to_pos(self._lastmax)+delta.x())
            self.setMinimum(new_min)
            self.setMaximum(new_max)
            self.update()
        else:
            val = self._to_value(event.pos().x())
            self.setSliderPosition(val)
            if self.hasTracking():
                self.setValue(val)
            self.update()

    def mouseReleaseEvent(self, event):
        if self._is_panning:
            self._is_panning = False
        else:
            self.setSliderPosition(self._to_value(event.pos().x()))

    def _to_pos(self, val):
        val-=self.minimum()
        val/=self.maximum()-self.minimum()+1
        val*=self.width()
        return int(val)

    def _to_value(self, x):
        x/=self.width()
        x*=self.maximum()-self.minimum()+1
        x+=self.minimum()
        return int(x)

    def paintEvent(self, event):
        import math
        painter = QPainter(self)

        # draw background
        painter.setPen(Qt.NoPen)
        painter.setBrush(self.palette().base().color())
        painter.drawRoundedRect(QRect(0, 0, self.width(), self.height()), 4,4)

        # draw ticks
        zoomfactor = self.width() / (self.maximum()+1 - self.minimum())

        step = int( 100 * math.pow(10, math.floor(math.log(1/zoomfactor, 10))) )
        if step<10:
            step=10
        tick_color = self.palette().text().color()
        tick_color.setAlpha(128)
        painter.setPen(QPen(tick_color, 0.0))
        first = self.minimum()//step*step
        last = (self.maximum()+step)//step*step

        for i in range(int(first), int(last), step//10):
            x = self._to_pos(i)
            if i%step==0:
                painter.drawLine(x,self.height()*1/2,x,self.height())
            elif i%step==5:
                painter.drawLine(x,self.height()*3/4,x,self.height())
            else:
                painter.drawLine(x,self.height()*9/10,x,self.height())

        # draw thumb
        x1 = self._to_pos(self.sliderPosition())
        x2 = self._to_pos(self.sliderPosition()+1)
        thumb_size = QSize(20, 20)

        c = QColor(self.palette().text().color())
        c.setAlpha(128)

        painter.setPen(Qt.NoPen)
        painter.setBrush(c)
        painter.drawRect(x1, 0, x2-x1, self.height())

        painter.setPen(QPen(self.palette().buttonText().color(), 1.0))
        painter.drawLine(x1+1, 0, x1+1, self.height())

        # draw frame value
        text_rect = QRect(x1, 0, self.width()-1-x1, self.height())
        painter.drawText(text_rect, Qt.AlignLeft, str(self.sliderPosition()))


        # painter.drawRect(x-thumb_size.width()/2, self.height()/2-thumb_size.height()/2, thumb_size.width(), thumb_size.height())

        # draw background rect
        
    def resizeEvent(self, event):
        self.update()

    def sizeHint(self):
        return QSize(100, 100)

    def minimumSizeHint(self):
        return QSize(100, 22)

    # def zoom(self):

    #     if not hasattr(self, '_zoom'):
    #         self._zoom = self.width() / (self.maximum() - self.minimum())
    #     return self._zoom

    # def setZoom(self, zoom):
    #     self._zoom = zoom

    #     # update min max
    #     center = (self.maximum() - self.minimum()) / 2
    #     print(center)
    #     new_min = center-self.width()/2*zoom
    #     new_max = center+self.width()/2*zoom

    #     self.setMinimum(new_min)
    #     self.setMaximum(new_max)

    # def wheelEvent(self, event):
    #     zoomSpeed = 0.001
    #     delta = -event.angleDelta().y() # consider implementing pixelDelta for macs
    #     zoomFactor = 1+delta*zoomSpeed
        
    #     # print(self._zoom * zoomFactor)
    #     self.setZoom(self._zoom * zoomFactor )
    #     # val = self._to_value(event.position().x())

    #     # delta_left = (self.minimum()-val)*zoomFactor
    #     # delta_right = (self.maximum()-val)*zoomFactor

    #     # self.setMaximum(val+delta_right)
    #     # self.setMinimum(val+delta_left)
        

    #     self.update()

if __name__ == "__main__":
    import sys, os
    app = QApplication(sys.argv)
    window = MySlider()
    window.resize(500, 100)
    window.setMinimum(100)
    window.setMaximum(300)
    window.show()
    app.exec_()
    os._exit(0)
