from PySide6.QtCore import *
from PySide6.QtWidgets import *
from PySide6.QtGui import *
import sys

class Viewer2D(QGraphicsView):
    zoomChanged = Signal(float)
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setRenderHint(QPainter.Antialiasing)
        self.setHorizontalScrollBarPolicy ( Qt.ScrollBarAlwaysOff )
        self.setVerticalScrollBarPolicy ( Qt.ScrollBarAlwaysOff )

        for gesture in [Qt.TapGesture, Qt.TapAndHoldGesture, Qt.PanGesture, Qt.PinchGesture, Qt.SwipeGesture, Qt.CustomGesture]:
            self.grabGesture(gesture)

        # crate temporary scene
        self.setScene(QGraphicsScene())
        self.setSceneRect(-sys.maxsize/4, -sys.maxsize/4, sys.maxsize/2, sys.maxsize/2) # x, y, w, h


        self.setBackgroundBrush(QBrush(QColor(240, 240, 240), Qt.SolidPattern))

        self.drawAxis = True
        self.drawGrid = True

        # self.setTransformationAnchor(QGraphicsView.NoAnchor)
        # self.setResizeAnchor(QGraphiwcsView.NoAnchor)

    def zoom(self):
        zoom_horizontal = self.transform().m11()
        zoom_vertical = self.transform().m22()
        return zoom_horizontal

    def setZoom(self, value):
        self.setTransformationAnchor(QGraphicsView.NoAnchor)
        self.setResizeAnchor(QGraphicsView.NoAnchor)
        oldPos = self.mapToScene(QPoint(self.width()/2, self.height()/2))

        zoom = self.zoom()
        self.scale(value/zoom, value/zoom)

        newPos = self.mapToScene(QPoint(self.width()/2, self.height()/2))
        delta = newPos - oldPos
        self.translate(delta.x(), delta.y())

        self.zoomChanged.emit(value)

    def event(self, event):
        if event.type() == QEvent.Gesture:
            return self.gestureEvent(event)
        return super().event(event)

    def gestureEvent(self, event):
        pinch = event.gesture(Qt.PinchGesture)
        if pinch:
            changeFlags = pinch.changeFlags()
            if changeFlags & QPinchGesture.ScaleFactorChanged:
                zoomFactor = pinch.scaleFactor()

                # GENTLE ZOOM
                # Set Anchors
                self.setTransformationAnchor(QGraphicsView.NoAnchor)
                self.setResizeAnchor(QGraphicsView.NoAnchor)
                
                # print(event.position())
                oldPos = self.mapToScene(self.mapFromGlobal(pinch.centerPoint().toPoint()))
                self.scale(zoomFactor, zoomFactor)
                newPos = self.mapToScene(self.mapFromGlobal(pinch.centerPoint().toPoint()))
                delta = newPos - oldPos
                self.translate(delta.x(), delta.y())

                # print("current: ", self.mapToScene(self.mapFromGlobal(pinch.centerPoint().toPoint())))
                # print("start:   ", pinch.startCenterPoint())
                # print("last:    ", self.mapToScene(self.mapFromGlobal(pinch.lastCenterPoint().toPoint())))
                # move scene to oldPosition
                self.zoomChanged.emit()
        return True

    def wheelEvent(self, event):
        zoomSpeed = 0.001
        delta = event.angleDelta().y() # consider implementing pixelDelta for macs
        zoomFactor = 1+delta*zoomSpeed

        # GENTLE ZOOM
        # Set Anchors
        self.setTransformationAnchor(QGraphicsView.NoAnchor)
        self.setResizeAnchor(QGraphicsView.NoAnchor)
        
        # print(event.position())
        oldPos = self.mapToScene(event.position().toPoint())
        self.scale(zoomFactor, zoomFactor)
        newPos = self.mapToScene(event.position().toPoint())
        delta = newPos - oldPos
        # print("delta", delta)
        self.translate(delta.x(), delta.y())
        # move scene to oldPosition
        self.zoomChanged.emit(self.zoom())


    def drawBackground(self, painter, rect):
        """ Draw background pattern """
        painter.setPen(Qt.NoPen)
        bgColor = self.palette().window().color()
        painter.setBrush(bgColor)
        painter.drawRect(rect)

        """Draw axis"""
        if self.drawAxis:
            painter.setPen(QPen(QColor(255,0,0), 0))
            painter.drawLine(0,0,100,0)
            painter.setPen(QPen(QColor(0,255,0), 0))
            painter.drawLine(0,0,0,100)

        """ Draw grid """
        if self.drawGrid:
            import math
            zoomfactor = self.transform().m11()
            gridSize = 300 * math.pow(10, math.floor(math.log(1/zoomfactor, 10)))
            gridSize = gridSize


            left = rect.left() - rect.left() % gridSize
            top = rect.top() - rect.top() % gridSize
     
            lines = [];
     
            x = left
            while x<rect.right():
                x+=gridSize
                lines.append(QLineF(x, rect.top(), x, rect.bottom()))

            y = top
            while y<rect.bottom():
                y+=gridSize
                lines.append(QLineF(rect.left(), y, rect.right(), y))
     
            painter.setPen(QPen(QBrush(QColor(128,128,128, 56)), 0))
            painter.drawLines(lines)


if __name__ == "__main__":
    import sys, os
    app = QApplication(sys.argv)
    window = Viewer2D()
    window.zoomChanged.connect(lambda val: print("zoom changed:", val))
    window.show()
    app.exec_()
    os._exit(0)
