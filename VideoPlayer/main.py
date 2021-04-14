import cv2

from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

import numpy as np

from datetime import datetime

import threading
import time

import string
from pathlib import Path
import os

from widgets.cachebar import CacheBar
from widgets.oscilloscope import Oscilloscope
from widgets.viewer2D import Viewer2D
import numbers
import psutil

from threading import Event, Thread

def setInterval(interval, func, *asrgs):
    stopped = Event()
    def loop():
        while not stopped.wait(interval): # the first call is in `interval` secs
            func(*args)
    Thread(target=loop).start()    
    return stopped.set


from reader import Reader
import OpenImageIO as oiio
from OpenImageIO import ImageBuf, ImageSpec, ROI, ImageBufAlgo

from invoke_in_main import inmain_later, inmain_decorator


            

def update_gui(state):
    pass

class PyVideoPlayer(QWidget):
    frame_loaded = Signal()
    state_changed = Signal()
    cache_updated = Signal()
    def __init__(self, parent=None):
        super().__init__(parent=parent)

        # self.setWindowFlags(Qt.FramelessWindowHint)

        self.state = {
            'path': None,
            'fps': 24,
            'frame': 0,
            'range': [0, 100],
            'cache': dict(),
            'memory_limit': 3000, # MB
            'playback': "paused", # forward | reverse | paused
            'zoom': "fit",
            'export': {
                'visible': False,
                'progress': 0,
                'filename': None
            },
            # computed
            'image': None,
            'memory': 0,
        }

        self._reader = None
        self._image_buffer:np.ndarray = None
        self.last_timestamp = None
        self.requested_frames = []

        self.worker = threading.Thread(target=self.preload, daemon=True)
        self.running = True
        self.read_lock = threading.Lock()
        self.worker.start()

        self.setWindowTitle("PyVideoPlayer")
        self.create_gui()
        self.state_changed.connect(self.update_gui)

        self.export_dialog = QDialog(self)
        self.export_dialog.hide()
        self.export_dialog.setLayout(QVBoxLayout())
        self.export_dialog.setWindowTitle("export")
        self.export_progress = QProgressBar(self.export_dialog)
        self.export_progress.setContextMenuPolicy(Qt.ActionsContextMenu)
        reveal_export_action = QAction("reveal", self)
        reveal_export_action.triggered.connect(lambda: print(self.state['export']['filename']))
        self.export_progress.addAction(reveal_export_action)
        self.export_dialog.layout().addWidget(self.export_progress)

        self.scrub_event = threading.Event()

    def open(self, filename=None):
        if not filename:
            filename, filters = QFileDialog.getOpenFileName(self, "Open Image", "/")

        if not filename:
            return
        
        # update video capture
        self.set_state(path=filename)

        # update viewer
        self.viewer.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)

    def evaluate(self, frame):
        # read file
        # return np.zeros((256, 256, 3))

        with self.read_lock:
            # time.sleep(0.5)
            data = self._reader.read(frame)

        return data

    def export(self, filename=None):
        if not filename:
            filename, filters = QFileDialog.getSaveFileName(self, "Export Video", "/", "*.mp4")

        if not filename:
            return

        self.set_state(export = {
            'visible': True,
            'filename': filename,
            'progress': 0
        })

        def run():
            path, ext = os.path.splitext(filename)
            assert ext == ".mp4"

            first_frame, last_frame = self.state['range']
            duration = last_frame-first_frame
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')

            self.export_progress.setMinimum(first_frame)
            self.export_progress.setMaximum(last_frame)
            self.export_progress.setFormat(filename+" %v/%m %p%")

            fps = self.state['fps']
            height, width, channels = self._reader.read(first_frame).shape
            writer = cv2.VideoWriter(filename,fourcc, fps, (width, height))
            for frame in range(first_frame, last_frame+1):
                progress = int(100*(frame-first_frame)/(last_frame-first_frame))
                # print(f"write frame: {frame}, {frame-first_frame}/{last_frame-first_frame} {progress}%")
                rgb = self.evaluate(frame).copy()
                bgr = rgb[...,::-1].copy()
                writer.write(bgr)

                self.set_state(export= {
                    'visible': self.state['export']['visible'],
                    'filename': filename,
                    'progress': frame
                })
            writer.release()

        the_thread = Thread(target=run, daemon=True).start()

    def preload(self):
        while self.running:
            time.sleep(0.00001)
            if self._reader:
                def used_memory():
                    megabytes = 0
                    for frame, (image, timestamp) in self.state['cache'].items():
                        megabytes+=image.nbytes / 1024 / 1024 # in MB
                    return megabytes
                while used_memory() > self.state['memory_limit'] and self.running:
                    oldest_frame = None
                    current_timestamp = datetime.now()
                    for frame, (image, timestamp) in self.state['cache'].items():
                        # print("search cache...")
                        # print(timestamp, current_timestamp>timestamp)
                        if timestamp<current_timestamp:
                            current_timestamp = timestamp
                            oldest_frame = frame

                    if oldest_frame is not None:
                        # print("delete frame:", oldest_frame)
                        del self.state['cache'][oldest_frame]
                        # self.cache_updated.emit()
                        self.set_state(cache=self.state['cache'])

                    # print("clean old cache")

                if self.requested_frames and self.running:
                    frame = self.requested_frames.pop()

                    if frame == self.state['frame']:
                        self.scrub_event.clear()

                    # print("preload frame", frame, threading.current_thread())
                    
                    img = self.evaluate(frame)
                    if frame == self.state['frame']:
                        self.scrub_event.set()
                    if img is not None:
                        with self.read_lock:
                            # print("read frame: ", frame)
                            self.state['cache'][frame] = (img, datetime.now())

                            # self.cache_updated.emit()
                            self.set_state(cache=self.state['cache'])

            else:
                # idle
                pass

    @inmain_decorator(wait_for_return=False)
    def set_state(self, **kwargs):
        # print("set state", threading.current_thread())
        assert threading.current_thread() is threading.main_thread()
        self.state.update(kwargs)

        changes = kwargs.copy()

        if 'range' in changes:
            assert isinstance(kwargs['range'][0], int)
            assert isinstance(kwargs['range'][1], int)

        # Calculate computed properties
        # -----------------------------

        # watch 'path' update range, fpr and clear cache
        if "path" in kwargs:
            # update reader
            self._reader = Reader(self.state['path'])

            # update range
            changes['range'] = (self._reader.first_frame, self._reader.last_frame)

            # update fps based on video
            changes['fps'] = self._reader.fps

            # clear cache
            changes['cache'] = dict()

        # watch range and set frame
        if 'range' in changes:
            # update frame
            if changes['range'][0]>self.state['frame']:
                changes['frame'] = changes['range'][0]
            if changes['range'][1]<self.state['frame']:
                changes['frame'] = changes['range'][1]

        # update state
        self.state.update(changes)

        # watch changes to request frames
        if "frame" in changes or "path" in changes or "cache" in changes:
            frame = self.state['frame']
            cache = self.state['cache']

            self.requested_frames = [f for f in [frame] if f not in cache]

        # compute 'image'
        if "frame" in changes or "path" in changes or "cache" in changes:
            frame = self.state['frame']
            cache = self.state['cache']
            if frame in cache:
                image, _ = cache[frame]
            else:
                image = None
            changes['image'] = image

        # compute 'memory'
        if "cache" in changes:
            megabytes = 0
            for frame, (image, timestamp) in self.state['cache'].items():
                megabytes+=image.nbytes / 1024 / 1024 # in MB
            changes['memory'] = megabytes

        if "export" in changes:
            if self.state['export']['visible'] != self.export_dialog.isVisible():
                if self.state['export']['visible']:
                    self.export_dialog.show()
                else:
                    self.export_dialog.hide()
        self.state.update(changes)
        
        # emit change signal
        # ------------------
        self.state_changed.emit()

    def create_gui(self):
        # View
        # ----
        self.setLayout(QVBoxLayout())
        self.layout().setContentsMargins(0,0,0,0)
        self.layout().setSpacing(0)

        # Create actions
        openAction = QAction("open", self)
        openAction.triggered.connect(self.open)

        exportAction = QAction("export", self)
        exportAction.triggered.connect(self.export)

        quitAction = QAction("quit", self)
        quitAction.triggered.connect(QApplication.quit)


        reverse_action = QAction("reverse", self)
        reverse_action.setShortcutContext(Qt.ApplicationShortcut)
        reverse_action.setShortcut("j")
        reverse_action.triggered.connect(lambda: self.set_state(playback="reverse"))
        forward_action = QAction("forward", self)
        forward_action.setShortcutContext(Qt.ApplicationShortcut)
        forward_action.setShortcut("l")
        forward_action.triggered.connect(lambda: self.set_state(playback="forward"))
        
        pause_action = QAction("pause", self)
        pause_action.setShortcutContext(Qt.ApplicationShortcut)
        pause_action.setShortcut("k")
        pause_action.triggered.connect(lambda: self.set_state(playback="paused"))

        frame_backwards_action = QAction("frame backwards")
        frame_backwards_action.setShortcutContext(Qt.ApplicationShortcut)
        frame_backwards_action.setShortcut('QKeySequence(Qt.LeftArrow)')
        frame_backwards_action.triggered.connect(lambda: self.set_state(frame=self.state['frame']-1))
        
        self.toggle_play_action = QAction("toggle_play", self)
        self.toggle_play_action.setCheckable(True)
        self.toggle_play_action.setShortcutContext(Qt.ApplicationShortcut)
        self.toggle_play_action.setShortcut(QKeySequence(Qt.Key_Space))

        def toggle_play():
            if self.state['playback'] == "forward":
                self.set_state(playback="paused")
            else:
                self.set_state(playback="forward")
        
        self.toggle_play_action.changed.connect(toggle_play)

        clear_cache_action = QAction("clear cache", self)
        clear_cache_action.triggered.connect(lambda: self.set_state(cache=dict()))

        fullscreen_action = QAction("fullscreen", self)
        fullscreen_action.setShortcutContext(Qt.ApplicationShortcut)
        fullscreen_action.triggered.connect(self.toggleFullscreen)
        fullscreen_action.setShortcutContext(Qt.ApplicationShortcut)
        fullscreen_action.setShortcut("u")

        fit_action = QAction("fit", self)
        fit_action.triggered.connect(self.fit)
        # Menu
        # ----

        ## File menu
        self.menuBar = QMenuBar(self)
        self.layout().addWidget(self.menuBar)
        fileMenu = self.menuBar.addMenu("File")

        fileMenu.addAction(openAction)
        fileMenu.addAction(exportAction)
        fileMenu.addAction(quitAction)

        ## Playback Menu
        playback_menu = self.menuBar.addMenu("Playback")
        playback_menu.addAction(reverse_action)
        playback_menu.addAction(forward_action)
        playback_menu.addAction(pause_action)
        playback_menu.addAction(self.toggle_play_action)
        playback_menu.addAction(clear_cache_action)

        ## View Menu
        view_menu = self.menuBar.addMenu("View")
        view_menu.addAction(fit_action)
        view_menu.addAction(fullscreen_action)

        ## Window menu
        windows_menu = self.menuBar.addMenu("Windows")

        # Widgets
        # ------
        
        # Viewer toolbar
        viewer_toolbar = QWidget()
        viewer_toolbar.setLayout(QHBoxLayout())

        self.layout().addWidget(viewer_toolbar)

        self.zoom_combo = QComboBox()
        self.zoom_combo.setToolTip("zoom")
        self.zoom_combo.addItem("fit")
        self.zoom_combo.addItem("10%")
        self.zoom_combo.addItem("25%")
        self.zoom_combo.addItem("50%")
        self.zoom_combo.addItem("100%")
        self.zoom_combo.addItem("200%")
        self.zoom_combo.addItem("400%")
        self.zoom_combo.addItem("800%")
        self.zoom_combo.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        self.zoom_combo.setEditable(True)
        self.zoom_combo.currentTextChanged.connect(lambda text: self.set_state(zoom=int(text[:-1])/100 if text[:-1].isnumeric() else text))
        viewer_toolbar.layout().addWidget(self.zoom_combo)

        viewer_toolbar.layout().addStretch()

        # Image Viewer
        self.viewer = Viewer2D()
        self.scene = QGraphicsScene()
        self.viewer.setScene(self.scene)
        self.viewer.zoomChanged.connect(lambda: self.set_state(zoom=self.viewer.zoom()))

        self.pix = QGraphicsPixmapItem()
        self.scene.addItem(self.pix)

        self.resolution_textitem = QGraphicsTextItem()
        self.resolution_textitem.setFlags(QGraphicsItem.ItemIgnoresTransformations) 
        self.scene.addItem(self.resolution_textitem)
        

        self.layout().addWidget(self.viewer)

        # Bottom Panel
        # ------------
        time_controls = QWidget()
        time_controls.setLayout(QHBoxLayout())
        time_controls.layout().setContentsMargins(0,0,0,0)
        # time_controls.layout().setSpacing(0)
        self.layout().addWidget(time_controls)

        slider_controls = QWidget(self)
        slider_controls.setLayout(QHBoxLayout())
        slider_controls.layout().setContentsMargins(0,0,0,0)
        slider_controls.layout().setSpacing(0)
        time_controls.layout().addWidget(slider_controls)

        # time_controls.layout().addSpacing(22)

        self.first_frame_spinner = QSpinBox()

        self.first_frame_spinner.setMinimum(-999999)
        self.first_frame_spinner.setMaximum(+999999)
        self.first_frame_spinner.setToolTip("first frame")
        slider_controls.layout().addWidget(self.first_frame_spinner)
        self.first_frame_spinner.valueChanged.connect(lambda val: self.set_state(range=(int(val), self.state['range'][1])))

        middle = QWidget()
        middle.setLayout(QVBoxLayout())
        middle.layout().setContentsMargins(16,0,16,0)
        middle.layout().setSpacing(0)
        slider_controls.layout().addWidget(middle)
        self.frame_slider = QSlider(Qt.Horizontal)
        def scrub(val):
            # wait for current frame to preload when scrubbing
            if self.state['playback'] in {"forward","reverse"}:
                self.set_state(playback="paused")
            self.scrub_event.wait(0.1) # seconds
            self.set_state(frame=val)
        self.frame_slider.valueChanged.connect(scrub)
        middle.layout().addWidget(self.frame_slider)
        self.cacheBar = CacheBar()
        middle.layout().addWidget(self.cacheBar)

        self.last_frame_spinner = QSpinBox()
        self.last_frame_spinner.setMinimum(-999999)
        self.last_frame_spinner.setMaximum(+999999)
        self.last_frame_spinner.setToolTip("last frame")
        slider_controls.layout().addWidget(self.last_frame_spinner)
        self.last_frame_spinner.valueChanged.connect(lambda val: self.set_state(range=(self.state['range'][0], int(val))))

        playback_controls = QWidget()
        playback_controls.setLayout(QHBoxLayout())
        playback_controls.layout().setContentsMargins(0,0,0,0)
        playback_controls.layout().setSpacing(0)
        time_controls.layout().addWidget(playback_controls)
        # playback_controls.layout().addStretch()


        self.fps_spinner = QSpinBox()
        self.fps_spinner.setToolTip("fps")
        self.fps_spinner.setSuffix("fps")
        self.fps_spinner.valueChanged.connect(lambda val: self.set_state(fps=val))
        playback_controls.layout().addWidget(self.fps_spinner)

        self.skip_to_start_btn = QPushButton("|<<")
        self.skip_to_start_btn.setFixedWidth(26)
        playback_controls.layout().addWidget(self.skip_to_start_btn)
        self.skip_to_start_btn.clicked.connect(lambda: self.set_state(frame=self.state['range'][0]))

        self.step_back_btn = QPushButton("|<")
        self.step_back_btn.setFixedWidth(26)
        playback_controls.layout().addWidget(self.step_back_btn)
        self.step_back_btn.clicked.connect(lambda: self.set_state(frame=self.state['frame']-1))

        self.reverse_btn = QPushButton("\u23F4")
        self.reverse_btn.setFixedWidth(26)
        self.reverse_btn.clicked.connect(lambda: self.set_state(playback="reverse"))
        playback_controls.layout().addWidget(self.reverse_btn)

        self.reverse_pause_btn = QPushButton("||")
        self.reverse_pause_btn.setVisible(False)
        self.reverse_pause_btn.setFixedWidth(26)
        self.reverse_pause_btn.clicked.connect(lambda: self.set_state(playback="paused"))
        playback_controls.layout().addWidget(self.reverse_pause_btn)

        self.frame_spinner = QSpinBox()
        self.frame_spinner.setAlignment(Qt.AlignHCenter)
        self.frame_spinner.setStyleSheet("QSpinBox{background-color:transparent}")
        self.frame_spinner.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.frame_spinner.setToolTip("current frame")
        self.frame_spinner.valueChanged.connect(lambda val: self.set_state(frame=val, playback="paused"))
        playback_controls.layout().addWidget(self.frame_spinner)

        self.forward_btn = QPushButton("\u23F5")
        self.forward_btn.setFixedWidth(26)
        self.forward_btn.clicked.connect(lambda: self.set_state(playback="forward"))
        playback_controls.layout().addWidget(self.forward_btn)

        self.pause_btn = QPushButton("||")
        self.pause_btn.setVisible(False)
        self.pause_btn.setFixedWidth(26)
        self.pause_btn.clicked.connect(lambda: pause_action.trigger())
        playback_controls.layout().addWidget(self.pause_btn)

        self.step_forward_btn = QPushButton(">|")
        self.step_forward_btn.setFixedWidth(26)
        playback_controls.layout().addWidget(self.step_forward_btn)
        self.step_forward_btn.clicked.connect(lambda: self.set_state(frame=self.state['frame']+1))

        self.skip_to_end_btn = QPushButton(">>|")
        self.skip_to_end_btn.setFixedWidth(26)
        playback_controls.layout().addWidget(self.skip_to_end_btn)
        self.skip_to_end_btn.clicked.connect(lambda: self.set_state(frame=self.state['range'][1]))

        for btn in [self.skip_to_start_btn, self.step_back_btn, self.reverse_pause_btn, self.reverse_btn, self.forward_btn, self.pause_btn, self.step_forward_btn, self.skip_to_end_btn]:
            btn.setFlat(True)

        # playback_controls.layout().addStretch()

        self.fps_label = QLabel("fps")
        self.fps_label.setFixedWidth(30)
        # bottom.layout().addWidget(self.fps_label)

        self.oscilloscope = Oscilloscope()
        self.oscilloscope.setMinimum(0)
        self.oscilloscope.setMaximum(self.state['fps']*2)
        self.oscilloscope.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        self.oscilloscope.resize(100,10)

        print("!!!!!!!!!", self.oscilloscope.size())

        self.statusbar = QStatusBar()
        self.layout().addWidget(self.statusbar)

        self.system_memory_label = QLabel("system memory")
        self.statusbar.addPermanentWidget(self.system_memory_label)

        self.path_label = QLabel()
        self.statusbar.addPermanentWidget(self.path_label)

        # memory
        self.memory_label = QLabel("memory")
        # self.memory_label.setFixedWidth(100)
        self.memory_spinner = QSpinBox()
        self.memory_spinner.setStyleSheet("QSpinBox{background-color:transparent}")
        self.memory_spinner.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.memory_spinner.setSuffix("MB")
        self.memory_spinner.setFrame(False)
        self.memory_spinner.setMinimum(0)
        self.memory_spinner.setMaximum(99999)
        self.memory_spinner.valueChanged.connect(lambda val: self.set_state(memory_limit=val))


        memory_controls = QWidget()
        memory_controls.setLayout(QHBoxLayout())
        memory_controls.layout().addWidget(self.memory_label)
        memory_controls.layout().addWidget(self.memory_spinner)
        memory_controls.layout().setContentsMargins(0,0,0,0)
        memory_controls.layout().setSpacing(0)
        self.statusbar.addPermanentWidget(memory_controls)

        self.resolution_label = QLabel("resolution")
        self.statusbar.addPermanentWidget(self.resolution_label)

        self.statusbar.addPermanentWidget(self.fps_label)
        self.statusbar.addPermanentWidget(self.oscilloscope)

        # timer
        self.timer = QTimer()
        print(self.timer.setTimerType(Qt.PreciseTimer))
        def next_frame():
            if self.state['playback'] == "forward":
                frame = self.state['frame']+1
                if frame>self.state['range'][1]:
                    frame = self.state['range'][0]
                self.set_state(frame=frame)

            elif self.state["playback"] == "reverse":
                frame = self.state['frame']-1
                if frame<self.state['range'][0]:
                    frame = self.state['range'][1]
                self.set_state(frame=frame)

        self.timer.timeout.connect(next_frame)

        self.dialog = QDialog(self)
        self.dialog.setLayout(QVBoxLayout())

        # show hide windows
        self.show_export_dialog_action = QAction("Export Window")
        self.show_export_dialog_action.setCheckable(True)
        def toggle_export_dialog(val):
            ex = self.state['export']
            ex.update({'visible': val})
            self.set_state(export = ex)

        self.show_export_dialog_action.toggled.connect(toggle_export_dialog)
        windows_menu.addAction(self.show_export_dialog_action)

    def toggleFullscreen(self):
        raise NotImplementedError
        # if self.dialog.isVisible():
        #     self.layout().addWidget(self.viewer)
        #     self.dialog.hide()
        # else:
        #     self.dialog.show()
        #     self.dialog.setWindowState(Qt.WindowFullScreen)
        #     self.dialog.layout().addWidget(self.viewer)

    def fit(self):
        self.set_state(zoom="fit")

    def update_gui(self):
        # print("update gui")
        ImageChanged = self.state['image'] is not None and self._image_buffer is not self.state['image']
        
        if ImageChanged:
            self._image_buffer = self.state['image']
            self._image_buffer.flags.writeable = False
            # IsEqual = str(self._image_buffer) == str(self.state['image'])
            # IsSame = self._image_buffer is self.state['image']
            # print( IsSame, IsEqual)

        # update gui
        if not self.export_dialog.isVisible() and self.state['export']['filename']:
            self.export_dialog.show()
            # print("export dialog not visible")

        else:
            if self.export_progress.value() != self.state['export']['progress']:
                self.export_progress.setValue(self.state['export']['progress'])

        # if self.state['export']['filename'] and not self.export_dialog.isVisible():
        #     if self.export_dialog
        #     self.export_dialog.show()

        # else:
        #     self.export_dialog.hide()

        if self.path_label.text() != self.state['path']:
            self.path_label.setText(self.state['path'])

        if self.fps_spinner.value() != self.state['fps']:
            self.fps_spinner.blockSignals(True)
            self.fps_spinner.setValue(self.state['fps'] or 0)
            self.fps_spinner.blockSignals(False)

        if self.memory_spinner.value() != self.state['memory_limit']:
            self.memory_spinner.blockSignals(True)
            self.memory_spinner.setValue(self.state['memory_limit'])
            self.memory_spinner.blockSignals(False)

        if self.frame_slider.value() != self.state['frame']:
            self.frame_slider.blockSignals(True)
            self.frame_slider.setValue(self.state['frame'])
            self.frame_slider.blockSignals(False)

        if (self.frame_slider.minimum(), self.frame_slider.maximum()) != self.state['range']:
            self.frame_slider.blockSignals(True)
            self.frame_slider.setMinimum(self.state['range'][0])
            self.frame_slider.setMaximum(self.state['range'][1])
            self.frame_slider.blockSignals(False)

        if self.frame_spinner.value() != self.state['frame']:
            self.frame_spinner.blockSignals(True)
            self.frame_spinner.setValue(self.state['frame'])
            self.frame_spinner.blockSignals(False)

        if (self.frame_spinner.minimum(), self.frame_spinner.maximum()) != self.state['range']:
            self.frame_spinner.blockSignals(True)
            self.frame_spinner.setMinimum(self.state['range'][0])
            self.frame_spinner.setMaximum(self.state['range'][1])
            self.frame_spinner.blockSignals(False)

        if self.first_frame_spinner.value() != self.state['range'][0]:
            self.first_frame_spinner.blockSignals(True)
            self.first_frame_spinner.setValue(self.state['range'][0])
            self.first_frame_spinner.blockSignals(False)

        if self.last_frame_spinner.value() != self.state['range'][1]:
            self.last_frame_spinner.blockSignals(True)
            self.last_frame_spinner.setValue(self.state['range'][1])
            self.last_frame_spinner.blockSignals(False)

        if self.cacheBar.range() != self.state['range']:
            self.cacheBar.setRange(*self.state['range'])
            
        if self.cacheBar.values() != self.state['cache'].keys():
            self.cacheBar.setValues([val for val in self.state['cache'].keys() ])

        if (self.state["playback"] == "forward") != self.toggle_play_action.isChecked():
            self.toggle_play_action.blockSignals(True)
            self.toggle_play_action.setChecked(self.state["playback"] == "forward")
            self.toggle_play_action.blockSignals(True)

        if self.state["playback"] == "forward":
            if not self.pause_btn.isVisible():
                self.pause_btn.setVisible(True)
            if self.forward_btn.isVisible():
                self.forward_btn.setVisible(False)
        else:
            if self.pause_btn.isVisible():
                self.pause_btn.setVisible(False)
            if not self.forward_btn.isVisible():
                self.forward_btn.setVisible(True)

        if self.state["playback"] == "reverse":
            if not self.reverse_pause_btn.isVisible():
                self.reverse_pause_btn.setVisible(True)
            if self.reverse_btn.isVisible():
                self.reverse_btn.setVisible(False)
        else:
            if self.reverse_pause_btn.isVisible():
                self.reverse_pause_btn.setVisible(False)
            if not self.reverse_btn.isVisible():
                self.reverse_btn.setVisible(True)

        high = self.state['fps']*2 if self.state['fps'] else 120
        if self.oscilloscope.maximum() != high:
            self.oscilloscope.setMaximum(high)

        if ImageChanged:
            # update viewer image
            height, width, channel = self.state['image'].shape
            bytesPerLine = 3 * width
            qImg = QImage(self.state['image'].data, width, height, bytesPerLine, QImage.Format_RGB888)
            self.pix.setPixmap(QPixmap(qImg))

        if ImageChanged:
            # update resolution label
            self.resolution_label.setText("{}x{}".format(width, height))

            self.resolution_textitem.setPos(width, height)
            self.resolution_textitem.setPlainText("{}x{}".format(width, height))

        if self.state['zoom'] == "fit":
            self.viewer.fitInView(self.pix.boundingRect(), Qt.KeepAspectRatio)

        elif self.viewer.zoom() != self.state['zoom']:
            # print("change zoom:", self.viewer.zoom(), self.state['zoom'])
            if isinstance(self.state['zoom'], numbers.Number):
                self.viewer.blockSignals(True)
                self.viewer.setZoom(self.state['zoom'])
                self.viewer.blockSignals(False)

        memory_text = "{:.0f}MB /".format(self.state['memory'])
        if self.memory_label.text() != memory_text:
            self.memory_label.setText(memory_text)

        zoom_text = "{:.0f}%".format(self.state['zoom']*100) if isinstance(self.state['zoom'], numbers.Number) else self.state['zoom']
        if self.zoom_combo.currentText() != zoom_text:
            self.zoom_combo.blockSignals(True)
            self.zoom_combo.setCurrentText(zoom_text)
            self.zoom_combo.blockSignals(False)

        total_memory = psutil.virtual_memory().total / (1024.0 ** 3)
        available_memory = psutil.virtual_memory().available / (1024.0 ** 3)
        system_memory_text = "system: {:.2f}/{:.2f}GB ".format(available_memory, total_memory)
        if self.system_memory_label.text() != system_memory_text:
            self.system_memory_label.setText(system_memory_text)

        if ImageChanged:
            # update fps counter
            timestamp = datetime.now()
            if self.last_timestamp:
                dt = (timestamp-self.last_timestamp).total_seconds()
                if dt>0:
                    self.fps_label.setText("{:.2f}".format(1/dt))
                    self.oscilloscope.push(1/dt)

            self.last_timestamp = timestamp

        # watch playback and start or stop timer
        if self.state['playback'] in {"forward", "reverse"}:
            if not self.timer.isActive():
                print("restart timer!", datetime.now())
                self.timer.start(round(1000/self.state['fps'] if self.state['fps'] else 0))

        if self.state['playback'] == "paused" and self.timer.isActive():
            print("pause timer", datetime.now())
            self.timer.stop()

        # update timer interval based on fps
        interval = 1000/self.state['fps'] if self.state['fps'] else 0
        if self.timer.interval() != interval:
            self.timer.setInterval(interval)

        # start/stop timer
        if self.state['playback'] in {"forward", "reverse"}:
            if self.state['frame'] not in self.state['cache']:
                if self.timer.isActive():
                    self.timer.stop()

            if self.state['frame'] in self.state['cache']:
                if not self.timer.isActive():
                    self.timer.start(1000/self.state['fps'] if self.state['fps'] else 0)

        elif self.state['playback'] == "paused":
            if self.timer.isActive():
                self.timer.stop()

    def resizeEvent(self, event):
        # uodate viewer
        if self.state['zoom'] == "fit":
            self.fit()

    def closeEvent(self, event):
        self.running = False
        print("close")

from widgets.themes import apply_dark_theme2

if __name__ == "__main__":

    import sys
    app = QApplication()

    extra = {
        # Button colors
        'danger': '#dc3545',
        'warning': '#ffc107',
        'success': '#17a2b8',

        # Font
        'font-family': 'Roboto',
    }

    apply_dark_theme2(app)
    
    window = PyVideoPlayer()
    window.show()
    if len(sys.argv)>1:
        print("argv:", sys.argv[1])
        window.open(sys.argv[1])
    else:
        pass
        window.open("../tests/MASA_sequence/MASA_sequence_00196.jpg")
        # window.open("../tests/Mása - becsukjuk, nem latszik.mp4")
        # window.open("R:/Frank/Preview/Andris/EF_VFX_04_MERGE_v56.mp4")
        # window.open("E:/_PREVIEW/EF_VFX_04_MERGE_v45/EF_VFX_04_MERGE_v45_93820.jpg")
        # window.open("E:/localize/EF_VFX_04/EF_VFX_04_0093230.dpx")
        # window.set_state(range=(93820, 93900))
    app.exec_()