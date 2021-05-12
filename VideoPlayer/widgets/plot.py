from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
from PySide6.QtSvg import QSvgRenderer

import matplotlib.pyplot as plt
import io
import math, random, time

class Plot(QWidget):
	def __init__(self, parent=None):
		super().__init__(parent=parent)

		self.renderer = QSvgRenderer()

	def paintEvent(self, event):
		painter = QPainter(self)
		plt.clf()
		plt.bar(['hello'], [math.sin(time.time())])
		f = io.StringIO()
		plt.savefig(f, format='svg')
		svg = f.getvalue()
		self.renderer.load(QByteArray(svg))
		self.renderer.render(painter)

if __name__=="__main__":
	app = QApplication.instance() or QApplication()
	widget = Plot()
	timer = QTimer()
	begin = time.time()

	@timer.timeout.connect
	def _():
		global begin
		widget.update()
		dt = time.time()-begin
		print(1/dt)
		begin = time.time()
	timer.start(1000/60)
	widget.show()
	app.exec_()