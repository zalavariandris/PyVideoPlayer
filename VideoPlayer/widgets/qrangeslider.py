#!/usr/bin/env python
# ---------------------------------------------------------------------------------------------
# Copyright (c) 2011-2014, Ryan Galloway (ryan@rsgalloway.com)
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#  - Redistributions of source code must retain the above copyright notice, this
#    list of conditions and the following disclaimer.
#
#  - Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
#  - Neither the name of the software nor the names of its contributors
#    may be used to endorse or promote products derived from this software
#    without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# ---------------------------------------------------------------------------------------------
# docs and latest version available for download at
#   http://rsgalloway.github.com/qrangeslider
# ---------------------------------------------------------------------------------------------

__author__ = "Ryan Galloway <ryan@rsgalloway.com>"
__version__ = "0.1.1"


# ---------------------------------------------------------------------------------------------
# SUMMARY
# ---------------------------------------------------------------------------------------------
"""The QRangeSlider class implements a horizontal range slider widget.

"""

# ---------------------------------------------------------------------------------------------
# TODO
# ---------------------------------------------------------------------------------------------

"""
  - smoother mouse move event handler
  - support splits and joins
  - verticle sliders
  - ticks
  
"""

# ---------------------------------------------------------------------------------------------
# IMPORTS
# ---------------------------------------------------------------------------------------------
import os
import sys

from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

# from PySide6 import uic

_fromUtf8 = lambda s: s

__all__ = ['QRangeSlider']

DEFAULT_CSS = """


QRangeSlider * {
    border: 0px;
    padding: 0px;
}

QRangeSlider Head,
QRangeSlider Tail {
    color: palette(alternate-base);
}

QRangeSlider #Span {
    background: palette(highlight);
}
QRangeSlider #Span:active {
    background: palette(Highlight);
}

QRangeSlider > QSplitter::handle {
    background: palette(Highlight);
}
QRangeSlider > QSplitter::handle:vertical {
    height: 4px;
}
QRangeSlider > QSplitter::handle:pressed {
    background: #ca5;
}

"""

def scale(val, src, dst):
    """
    Scale the given value from the scale of src to the scale of dst.
    """
    return int(((val - src[0]) / float(src[1]-src[0])) * (dst[1]-dst[0]) + dst[0])

class Ui_Form(object):
    """default range slider form"""
    
    def setupUi(self, Form):
        Form.setObjectName(_fromUtf8("QRangeSlider"))
        Form.resize(300, 30)
        Form.setStyleSheet(_fromUtf8(DEFAULT_CSS))
        self.gridLayout = QGridLayout(Form)
        self.gridLayout.setContentsMargins(0,0,0,0)
        self.gridLayout.setSpacing(0)
        self.gridLayout.setObjectName(_fromUtf8("gridLayout"))
        self._splitter = QSplitter(Form)
        self._splitter.setMinimumSize(QSize(0, 0))
        self._splitter.setMaximumSize(QSize(16777215, 16777215))
        self._splitter.setOrientation(Qt.Horizontal)
        self._splitter.setObjectName(_fromUtf8("splitter"))
        self._head = QGroupBox(self._splitter)
        self._head.setTitle(_fromUtf8(""))
        self._head.setObjectName(_fromUtf8("Head"))
        self._handle = QGroupBox(self._splitter)
        self._handle.setTitle(_fromUtf8(""))
        self._handle.setObjectName(_fromUtf8("Span"))
        self._tail = QGroupBox(self._splitter)
        self._tail.setTitle(_fromUtf8(""))
        self._tail.setObjectName(_fromUtf8("Tail"))
        self.gridLayout.addWidget(self._splitter, 0, 0, 1, 1)

        # self.retranslateUi(Form)
        QMetaObject.connectSlotsByName(Form)

    def retranslateUi(self, Form):
        encoding = QApplication.UnicodeUTF8
        Form.setWindowTitle(QApplication.translate("QRangeSlider", 
                                                         "QRangeSlider",
                                                         None, encoding))


class Element(QGroupBox):
    
    def __init__(self, parent, main):
        super(Element, self).__init__(parent)
        self.main = main
        
    def setStyleSheet(self, style):
        """redirect style to parent groupbox"""
        self.parent().setStyleSheet(style)

    def textColor(self):
        """text paint color"""
        return getattr(self, '__textColor', self.palette().text().color())

    def setTextColor(self, color):
        """set the text paint color"""
        if type(color) == tuple and len(color) == 3:
            color = QColor(color[0], color[1], color[2])
        elif type(color) == int:
            color = QColor(color, color, color)
        setattr(self, '__textColor', color)

    def paintEvent(self, event):
        """overrides paint event to handle text"""
        qp = QPainter()
        qp.begin(self)
        if self.main.drawValues():
            self.drawText(event, qp)
        qp.end()


class Head(Element):
    """area before the handle"""
    
    def __init__(self, parent, main):
        super(Head, self).__init__(parent, main)

    def drawText(self, event, qp):
        # qp.setPen(self.textColor())
        # qp.setFont(QFont('Arial', 10))
        qp.drawText(event.rect(), Qt.AlignLeft, str(self.main.minimum()))


class Tail(Element):
    """area after the handle"""
    
    def __init__(self, parent, main):
        super(Tail, self).__init__(parent, main)
        
    def drawText(self, event, qp):
        # qp.setPen(self.textColor())
        # qp.setFont(QFont('Arial', 10))
        qp.drawText(event.rect(), Qt.AlignRight, str(self.main.maximum()))


class Handle(Element):
    """handle area"""
    
    def __init__(self, parent, main):
        super(Handle, self).__init__(parent, main)
        
    def drawText(self, event, qp):
        qp.setPen(self.textColor())
        qp.setFont(QFont('Arial', 10))
        qp.drawText(event.rect(), Qt.AlignLeft, str(self.main.start()))
        qp.drawText(event.rect(), Qt.AlignRight, str(self.main.end()))

    def mouseMoveEvent(self, event):
        event.accept()
        mx = event.globalX()
        _mx = getattr(self, '__mx', None)
        
        if not _mx:  
            setattr(self, '__mx', mx)
            dx = 0
        else:
            dx = mx - _mx

        setattr(self, '__mx', mx)

        if dx == 0:
            event.ignore()
            return
        elif dx > 0:
            dx = 1
        elif dx < 0:
            dx = -1
        
        s = self.main.start() + dx
        e = self.main.end() + dx
        if s >= self.main.minimum() and e <= self.main.maximum():
            self.main.setRange(s, e)


class QRangeSlider(QWidget, Ui_Form):
    """
    The QRangeSlider class implements a horizontal range slider widget.

    Inherits QWidget.

    Methods

        * __init__ (self, QWidget parent = None)
        * bool drawValues (self)
        * int end (self)
        * (int, int) getRange (self)
        * int max (self)
        * int min (self)
        * int start (self)
        * setBackgroundStyle (self, QString styleSheet)
        * setDrawValues (self, bool draw)
        * setEnd (self, int end)
        * setStart (self, int start)
        * setRange (self, int start, int end)
        * setSpanStyle (self, QString styleSheet)

    Signals

        * endValueChanged (int)
        * maximumChanged (int)
        * minimumChanged (int)
        * startValueChanged (int)

    Customizing QRangeSlider

    You can style the range slider as below:
    ::
        QRangeSlider * {
            border: 0px;
            padding: 0px;
        }
        QRangeSlider #Head {
            background: #222;
        }
        QRangeSlider #Span {
            background: #393;
        }
        QRangeSlider #Span:active {
            background: #282;
        }
        QRangeSlider #Tail {
            background: #222;
        }

    Styling the range slider handles follows QSplitter options:
    ::
        QRangeSlider > QSplitter::handle {
            background: #393;
        }
        QRangeSlider > QSplitter::handle:vertical {
            height: 4px;
        }
        QRangeSlider > QSplitter::handle:pressed {
            background: #ca5;
        }
        
    """

    # define splitter indices
    _SPLIT_START = 1
    _SPLIT_END = 2

    # signals
    minimumChanged = Signal(int)
    maximumChanged = Signal(int)
    startValueChanged = Signal(int)
    endValueChanged = Signal(int)

    def __init__(self, parent=None):
        """Create a new QRangeSlider instance.
        
            :param parent: QWidget parent
            :return: New QRangeSlider instance.
        
        """
        super(QRangeSlider, self).__init__(parent)
        self.setupUi(self)
        self.setMouseTracking(False)

        #self._splitter.setChildrenCollapsible(False)
        self._splitter.splitterMoved.connect(self._handleMoveSplitter)

        # head layout
        self._head_layout = QHBoxLayout()
        self._head_layout.setSpacing(0)
        self._head_layout.setContentsMargins(0,0,0,0)
        self._head.setLayout(self._head_layout)
        self.head = Head(self._head, main=self)
        self._head_layout.addWidget(self.head)

        # handle layout
        self._handle_layout = QHBoxLayout()
        self._handle_layout.setSpacing(0)
        self._handle_layout.setContentsMargins(0,0,0,0)
        self._handle.setLayout(self._handle_layout)
        self.handle = Handle(self._handle, main=self)
        self._handle_layout.addWidget(self.handle)

        # tail layout
        self._tail_layout = QHBoxLayout()
        self._tail_layout.setSpacing(0)
        self._tail_layout.setContentsMargins(0,0,0,0)
        self._tail.setLayout(self._tail_layout)
        self.tail = Tail(self._tail, main=self)
        self._tail_layout.addWidget(self.tail)

        # defaults
        self.setMinimum(0)
        self.setMaximum(99)
        self.setStart(0)
        self.setEnd(99)
        self.setDrawValues(True)

    def minimum(self):
        """:return: minimum value"""
        return getattr(self, '__min', None)

    def maximum(self):
        """:return: maximum value"""
        return getattr(self, '__max', None)
    
    def setMinimum(self, value):
        """sets minimum value"""
        assert type(value) is int
        setattr(self, '__min', value)
        self.minimumChanged.emit(value)

    def setMaximum(self, value):
        """sets maximum value"""
        assert type(value) is int
        setattr(self, '__max', value)
        self.maximumChanged.emit(value)
    
    def start(self):
        """:return: range slider start value"""
        return getattr(self, '__start', None)

    def end(self):
        """:return: range slider end value"""
        return getattr(self, '__end', None)

    def _setStart(self, value):
        """stores the start value only"""
        setattr(self, '__start', value)
        self.startValueChanged.emit(value)
    
    def setStart(self, value):
        """sets the range slider start value"""
        assert type(value) is int
        v = self._valueToPos(value)
        self._splitter.splitterMoved.disconnect()
        self._splitter.moveSplitter(v, self._SPLIT_START)
        self._splitter.splitterMoved.connect(self._handleMoveSplitter)
        self._setStart(value)
        self.handle.update()

    def _setEnd(self, value):
        """stores the end value only"""
        setattr(self, '__end', value)
        self.endValueChanged.emit(value)
    
    def setEnd(self, value):
        """set the range slider end value"""
        assert type(value) is int
        v = self._valueToPos(value)
        self._splitter.splitterMoved.disconnect()
        self._splitter.moveSplitter(v, self._SPLIT_END)
        self._splitter.splitterMoved.connect(self._handleMoveSplitter)
        self._setEnd(value)
        self.handle.update()

    def drawValues(self):
        """:return: True if slider values will be drawn"""
        return getattr(self, '__drawValues', None)
    
    def setDrawValues(self, draw):
        """sets draw values boolean to draw slider values"""
        assert type(draw) is bool
        setattr(self, '__drawValues', draw)

    def getRange(self):
        """:return: the start and end values as a tuple"""
        return (self.start(), self.end())

    def setRange(self, start, end):
        """set the start and end values"""
        self.setStart(start)
        self.setEnd(end)
        
    def keyPressEvent(self, event):
        """overrides key press event to move range left and right"""
        key = event.key()
        if key == Qt.Key_Left:
            s = self.start()-1
            e = self.end()-1
        elif key == Qt.Key_Right:
            s = self.start()+1
            e = self.end()+1
        else:
            event.ignore()
            return
        event.accept()
        if s >= self.minimum() and e <= self.maximum():
            self.setRange(s, e)

    def setBackgroundStyle(self, style):
        """sets background style"""
        self._tail.setStyleSheet(style)
        self._head.setStyleSheet(style)

    def setSpanStyle(self, style):
        """sets range span handle style"""
        self._handle.setStyleSheet(style)

    def _valueToPos(self, value):
        """converts slider value to local pixel x coord"""
        return scale(value, (self.minimum(), self.maximum()), (0, self.width()))

    def _posToValue(self, xpos):
        """converts local pixel x coord to slider value"""
        return scale(xpos, (0, self.width()), (self.minimum(), self.maximum()))

    def _handleMoveSplitter(self, xpos, index):
        """private method for handling moving splitter handles"""
        hw = self._splitter.handleWidth()
        
        def _lockWidth(widget):
            width = widget.size().width()
            widget.setMinimumWidth(width)
            widget.setMaximumWidth(width)
            
        def _unlockWidth(widget):
            widget.setMinimumWidth(0)
            widget.setMaximumWidth(16777215)
        
        v = self._posToValue(xpos)
        
        if index == self._SPLIT_START:
            _lockWidth(self._tail)
            if v >= self.end():
                return
            
            offset = -20
            w = xpos + offset
            self._setStart(v)
            
        elif index == self._SPLIT_END:
            _lockWidth(self._head)
            if v <= self.start():
                return
            
            offset = -40
            w = self.width() - xpos + offset
            self._setEnd(v)

        _unlockWidth(self._tail)
        _unlockWidth(self._head)
        _unlockWidth(self._handle)


#-------------------------------------------------------------------------------
# MAIN
#-------------------------------------------------------------------------------

if __name__ == '__main__':
    app = QApplication(sys.argv)
    rs = QRangeSlider()
    rs.show()
    rs.setMinimum(10)
    rs.setMaximum(120)
    rs.setRange(15, 35)
    # rs.setBackgroundStyle('background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #222, stop:1 #333);')
    # rs.handle.setStyleSheet('background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #282, stop:1 #393);')
    app.exec_()