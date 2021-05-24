from PySide6.QtWidgets import *
from PySide6.QtCore import *

import OpenImageIO as oiio
import time
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor


def evaluate(path, lut=None, frame=0):
    # image = oiio.ImageBuf(path)
    time.sleep(frame+0.5)
    # pixels = image.get_pixels()
    key = frame
    return key, "hello"

# class Worker(QObject):
#     finished = Signal(str)
#     error = Signal()
#     def __init__(self, parent=None):
#         super().__init__(parent=parent)
#         self.result = None

#     def evaluate(self, path):
#         self.result = evaluate(path)
#         self.finished.emit(path)

class FramePool:
    def __init__(self):
        self.cache = dict()

    def request_frames(self, path, lut, frame)->:
        pass

class Window(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)

        path = "../tests/resources/MASA_sequence/MASA_sequence_00196.jpg"
        lut = None
        frame = 196

        run_button = QPushButton("run")
        self.setLayout(QHBoxLayout())
        self.layout().addWidget(run_button)
        @run_button.clicked.connect
        def on_click():
            for i in range(5):
                future = self.request_frame(path, lut, i)

                @future.add_done_callback
                def when_done(future):
                    key, res = future.result()
                    print("done:", key, res)
                print("after request")

    def request_frame(self, path, lut, frame):
        executor = ThreadPoolExecutor(max_workers=1)

        future = executor.submit(evaluate, path, lut, frame)
        return future

if __name__ == "__main__":
    from pathlib import Path
    path = "../tests/resources/MASA_sequence/MASA_sequence_00196.jpg"
    assert Path(path).exists()
    # res = evaluate(path)

    app = QApplication.instance() or QApplication()

    window = Window()
    window.show()

    # worker = Worker()
    # worker_thread = QThread(app)
    # worker = Worker()
    # worker.moveToThread(worker_thread)
    # worker_thread.started.connect(lambda: worker.evaluate(path))
    # worker_thread.start()

    # @worker.finished.connect
    # def _(key):
    #     pixels = worker.result
    #     print("finished {}: {}".format(key, pixels.shape))

    # worker_thread.finished.connect(worker.deleteLater)

    # window = Window()
    # window.show()

    # @app.lastWindowClosed.connect
    # def _():
    #     worker_thread.quit()

    print("run")
    app.exec_()

