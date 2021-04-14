from threading import Event, Thread

class Timer:
	timeout = Signal()
	def __init__(self):
		self._isActive = False
		self._interval = 1000/24 # ms float
		self._stopped = Event()
		self._thread = Thread(target=self.loop)

	def stop(self):
		pass

	def start(self):
		self._isActive = True
		self._thread.start()
		self._stopped.set

	def loop(self):
		while not self._stopped(self._interval):
			self.timeout.emit()

	def setInterval(self, value):
		self._interval = value

	def isActive(self):
		return self._isActive

if __name__ == "__main__":
	timer = Timer()
	timer.timeout.connect(lambda: print("hello"))
