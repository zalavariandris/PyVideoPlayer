from PySide6.QtCore import *
from PySide6.QtWidgets import *
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer
from pathlib import Path


class QWatchdog(QObject, FileSystemEventHandler, Observer):
    modified_signal = Signal(str)
    def __init__(self, path, parent=None):
        QObject.__init__(self, parent=parent)
        FileSystemEventHandler.__init__(self)
        Observer.__init__(self)

        self._path = path
        self.schedule(self, Path(self.path).parent, recursive=False)
        self.start()

        self.destroyed.connect(self._cleanup)

    def _cleanup(self):
        self.stop()
        self.join()

    def on_modified(self, event):
        if Path(event.src_path) == Path(self._path):
            self.modified_signal.emit(event.src_path)

    @property
    def path(self):
        return self._path


class QSSHotreload(QWatchdog):
    def __init__(self, path, parent=None):
        super().__init__(path, parent=parent)

        self.reload_qss()
        self.modified_signal.connect(self.reload_qss)

    def reload_qss(self):
        app = QApplication.instance()
        text = Path(self.path).read_text()
        app.setStyleSheet(text)


def main():
    app = QApplication.instance() or QApplication()

    window = QWidget()
    window.show()

    hotreload = QSSHotreload("./stylesheet.qss", parent=window)

    app.exec()

if __name__ == "__main__":
    main()
