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
from widgets.lineardial import LinearDial
import numbers
import psutil

from threading import Event, Thread

from read import Reader
import OpenImageIO as oiio
from OpenImageIO import ImageBuf, ImageSpec, ROI, ImageBufAlgo,ImageOutput

from invoke_in_main import inmain_later, inmain_decorator
from utils import on

from widgets.qrangeslider import QRangeSlider

from widgets.myslider import MySlider
from widgets.myrangeslider import MyRangeSlider

from dataclasses import dataclass

from LUT import read_lut, apply_lut

import mimetypes

def evaluate(self, frame: int, image_path: str, downsample: int, lut_path: str, rect=None)->np.ndarray:
    return pixels

class Viewer2D(Viewer2D):
    valueChanged = Signal(int)
    minimumChanged = Signal(int)
    maximumChanged = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self._value = 0
        self._minimum = 0
        self._maximum = 99

        self._is_scrubbing = False
        self._last_pos = None
        self._last_value = None

        self._wrapping = False

    def setWrapping(self, val):
        self._wrapping = val

    def wrapping(self):
        return self._wrapping

    def minimum(self):
        return self._minimum

    def setMinimum(self, val):
        self._minimum = val
        self.minimumChanged.emit(val)

    def maximum(self):
        return self._maximum

    def setMaximum(self, val):
        self._maximum = val
        self.maximumChanged.emit(val)

    def value(self):
        return self._value

    def setValue(self, val):
        if self._wrapping:
            if val<self._minimum:
                val = self._maximum - (self._minimum-val)+1
            if val>self._maximum:
                val = self._minimum + (val-self._maximum)-1
        else:
            if val < self._minimum or val > self._maximum:
                return
        self._value = val
        self.valueChanged.emit(val)

    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            self._last_pos = event.pos()
            self._last_value = self._value
            self._is_scrubbing = True
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._is_scrubbing:
            delta = event.pos() - self._last_pos
            value = self._last_value + (delta.x()-delta.y())/10
            self.setValue(value)
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._is_scrubbing:
            self._is_scrubbing = False
        else:
            super().mouseReleaseEvent(event)

            
class PyVideoPlayer(QWidget):
    frame_loaded = Signal()
    state_changed = Signal(dict)
    cache_updated = Signal()
    def __init__(self, parent=None):
        super().__init__(parent=parent)

        # self.setWindowFlags(Qt.FramelessWindowHint)

        self.times = {}

        self.state = {
            'path': None,
            'fps': 24,
            'frame': 0,
            'range': [0, 100],
            'inpoint': 0,
            'outpoint': 100,
            'cache': dict(),
            'memory_limit': 3000, # MB
            'playback': "paused", # forward | reverse | paused
            'zoom': "fit",
            
            'export': {
                'visible': False,
                'progress': 0,
                'filename': None
            },

            'lut_path': None,
            'lut_enabled': False,
            # computed
            'image': None,
            'downsample': 'full', # full half | quarter
            'memory': 0,
        }

        self._cache = dict()
        self._lut = None
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

        self.setAcceptDrops(True)
        self.viewer.setAcceptDrops(False)

    def dragEnterEvent(self, event):
        print('drag enter', event)
        if event.mimeData().hasUrls():
            url = event.mimeData().urls()[0]
            if url.isLocalFile():
                path = url.path()
                mime, encoding = mimetypes.guess_type(path)
                if mime:
                    IsVideo = mime.split("/")[0] == 'video'
                    IsImage = mime.split("/")[0] == 'image'
                    if IsVideo or IsImage:
                        event.acceptProposedAction()

    def dropEvent(self, event):
        path = event.mimeData().urls()[0].path(QUrl.FullyDecoded)[1:]
        print("open path:", Path(path))
        self.open(path)

    def open(self, filename=None):
        if not filename:
            filename, filters = QFileDialog.getOpenFileName(self, "Open Image", "/")

        if not filename:
            return
        
        # update video capture
        self.set_state(path=filename)

        # # update viewer
        # self.viewer.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)

    def open_lut(self, filename=None):
        if not filename:
            filename, filters = QFileDialog.getOpenFileName()

        if not filename:
            return

        self.set_state(lut_path=filename, lut_enabled=True)

    def evaluate(self, frame, downsample, rect=None):
        # read file
        # return np.zeros((256, 256, 3))

        with self.read_lock:
            idx = ['full', 'half', 'quarter'].index(downsample)
            factor = [1,2,4][idx]

            begin = time.time()
            data = self._reader.read(frame)
            self.times['read'] = time.time()-begin

            begin = time.time()
            data = cv2.resize(data, 
                dsize=(data.shape[1]//factor, data.shape[0]//factor), 
                interpolation=cv2.INTER_NEAREST)
            self.times['resize'] = time.time()-begin

            begin = time.time()
            if self._lut is not None and self.state['lut_enabled']:
                data = apply_lut(data.astype(np.float32)/255, self._lut)*255
                data = data.astype(np.uint8)
            self.times['lut'] = time.time()-begin

        return data

    def export(self, filename=None):
        if not filename:
            filename, filters = QFileDialog.getSaveFileName(self, "Export Video", "/", "*.mp4;; *.jpg")

        if not filename:
            return

        self.set_state(export = {
            'visible': True,
            'filename': filename,
            'progress': 0
        })

        # set widget
        first_frame, last_frame = self.state['range']
        self.export_progress.setMinimum(first_frame)
        self.export_progress.setMaximum(last_frame)
        self.export_progress.setFormat(filename+" %v %p%")

        def run():
            path, ext = os.path.splitext(filename)
            assert ext in {'.mp4', '.jpg'}

            first_frame, last_frame = self.state['range']
            duration = last_frame-first_frame
            fps = self.state['fps']
            height, width, channels = self.evaluate(first_frame).shape

            IsSequence = ext == ".jpg"
            IsMovie = ext == ".mp4"

            if IsSequence:
                for frame in range(first_frame, last_frame+1):
                    progress = int(100*(frame-first_frame)/(last_frame-first_frame))

                    rgb = self.evaluate(frame).copy()
                    assert rgb.shape == (height, width, channels)
                    bgr = rgb[...,::-1].copy()
                    
                    frame_filename = path+("%05d" % frame)+ext
                    print("create output", frame_filename)
                    out = ImageOutput.create(frame_filename)
                    if not out:
                        print(ext, "format is not supported")
                        return
                    spec = ImageSpec(width, height, channels, oiio.TypeUInt8)

                    print("wrtie image")
                    out.open(frame_filename, spec)
                    out.write_image(bgr)
                    out.close()

                    # update state
                    self.set_state(export= {
                        'visible': self.state['export']['visible'],
                        'filename': filename,
                        'progress': frame
                    })

            if IsMovie:
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                writer = cv2.VideoWriter(filename,fourcc, fps, (width, height))
                for frame in range(first_frame, last_frame+1):
                    progress = int(100*(frame-first_frame)/(last_frame-first_frame))
                    
                    rgb = self.evaluate(frame).copy()
                    bgr = rgb[...,::-1].copy()
                    writer.write(bgr)

                    # update state
                    self.set_state(export= {
                        'visible': self.state['export']['visible'],
                        'filename': filename,
                        'progress': frame
                    })
                writer.release()

        the_thread = Thread(target=run, daemon=True).start()

    # def get_cache(self, frame, res):
    #     return self._cache[(frame, res)]

    # def has_cache(self, frame, res):
    #     return (frame, res) in self._cache

    # def set_cache(self, frame, res, img):
    #     self._cache[(frame, res)] = img

    # def cache(self):
    #     for (frame, res) in self.state['cache']:
    #         yield frame, res

    def preload(self):
        while self.running:
            time.sleep(0.00001)
            if self._reader:
                def used_memory():
                    megabytes = 0
                    for (frame, downsample, lut), (image, timestamp) in self.state['cache'].items():
                        megabytes+=image.nbytes / 1024 / 1024 # in MB
                    return megabytes
                while used_memory() > self.state['memory_limit'] and self.running:
                    oldest_key = None
                    current_timestamp = datetime.now()
                    for (frame, downsample, lut), (image, timestamp) in self.state['cache'].items():
                        # print("search cache...")
                        # print(timestamp, current_timestamp>timestamp)
                        if timestamp<current_timestamp:
                            current_timestamp = timestamp
                            oldest_key = (frame, downsample, lut)

                    if oldest_key is not None:
                        # print("delete frame:", oldest_frame)
                        del self.state['cache'][oldest_key]
                        # self.cache_updated.emit()
                        self.set_state(cache=self.state['cache'])

                    # print("clean old cache")

                if self.requested_frames and self.running:
                    (frame, downsample, lut) = self.requested_frames.pop()

                    if frame == self.state['frame']:
                        self.scrub_event.clear()

                    # print("preload frame", frame, threading.current_thread())
                    
                    img = self.evaluate(frame, downsample)
                    if frame == self.state['frame']:
                        self.scrub_event.set()
                    if img is not None:
                        with self.read_lock:
                            # print("read frame: ", frame)
                            downsample = self.state['downsample']
                            lut = self.state['lut_path'] if self.state['lut_enabled'] else None
                            self.state['cache'][(frame, downsample, lut)] = (img, datetime.now())

                            # self.cache_updated.emit()
                            self.set_state(cache=self.state['cache'])

            else:
                # idle
                pass

    @inmain_decorator(wait_for_return=False)
    def set_state(self, **kwargs):
        print("set state", kwargs.keys())
        assert threading.current_thread() is threading.main_thread()
        self.state.update(kwargs)

        changes = kwargs.copy()

        if 'range' in changes:
            assert isinstance(changes['range'][0], int)
            assert isinstance(changes['range'][1], int)

            if changes['range'][0]>changes['range'][1]:
                del changes['range']

        # Calculate computed properties
        # -----------------------------

        # watch 'path' update range, fpr and clear cache
        if "path" in changes:
            # update reader
            self._reader = Reader(self.state['path'])

            # update range
            changes['range'] = (self._reader.first_frame, self._reader.last_frame)

            changes['frame'] = self._reader.first_frame

            changes['inpoint'] = self._reader.first_frame
            changes['outpoint'] = self._reader.last_frame

            # update fps based on video
            changes['fps'] = self._reader.fps

            # clear cache
            changes['cache'] = dict()

            print("zoom at path change")
            changes['zoom'] = "fit"


        if "lut_path" in changes:
            self._lut = read_lut(changes['lut_path'])

        # # watch range and set frame
        # if 'range' in changes:
        #     # update frame
        #     if changes['range'][0]>self.state['frame']:
        #         changes['frame'] = changes['range'][0]
        #     if changes['range'][1]<self.state['frame']:
        #         changes['frame'] = changes['range'][1]

        # # watch range set in and out points
        # if 'range' in changes:
        #     if changes['range'][0]>changes.get('inpoint', self.state['inpoint']):
        #         changes['inpoint'] = changes['range'][0]
        #     if changes['range'][1]<changes.get('outpoint', self.state['outpoint']):
        #         changes['outpoint'] = changes['range'][1]

        # update state
        self.state.update(changes)

        # watch changes to request frames
        if any(['frame', 'path', 'cache', 'downsample', 'lut_enabled', 'lut_path'] for key in changes):
            frame = changes.get('frame', self.state['frame'])
            cache = changes.get('cache', self.state['cache'])
            downsample = changes.get('downsample', self.state['downsample'])
            lut_path = changes.get('lut_path', self.state['lut_path'])
            lut_enabled = changes.get('lut_enabled', self.state['lut_enabled'])
            lut = lut_path if lut_enabled else None
            frames = [(f, downsample, lut) for f in [frame] if (f, downsample, lut) not in cache]
            self.requested_frames = frames

        # compute 'image'
        if any(['frame', 'path', 'cache', 'downsample', 'lut_enabled', 'lut_path'] for key in changes):
            frame = changes.get('frame', self.state['frame'])
            downsample = self.state['downsample']
            lut_path = changes.get('lut_path', self.state['lut_path'])
            lut_enabled = changes.get('lut_enabled', self.state['lut_enabled'])
            lut = lut_path if lut_enabled else None
            if (frame, downsample, lut) in self.state['cache']:
                image, _ = self.state['cache'][(frame, downsample, lut)]
            else:
                image = None

            changes['image'] = image

        # compute 'memory'
        if "cache" in changes:
            cache = changes.get('cache', self.state['cache'])
            megabytes = 0
            for (frame, downsample, lut), (image, timestamp) in cache.items():
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
        self.state_changed.emit(changes)

    
    def create_menubar(self):
        # Actions
        # ----
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

        set_inpoint_action = QAction("set in point", self)
        set_inpoint_action.setShortcutContext(Qt.ApplicationShortcut)
        set_inpoint_action.setShortcut('i')
        set_inpoint_action.triggered.connect(lambda: self.set_state(inpoint=self.state['frame']))
        set_outpoint_action = QAction('set out point', self)
        set_outpoint_action.setShortcutContext(Qt.ApplicationShortcut)
        set_outpoint_action.setShortcut('o')
        set_outpoint_action.triggered.connect(lambda: self.set_state(outpoint=self.state['frame']))

        def toggle_play():
            if self.state['playback'] == "forward":
                self.set_state(playback="paused")
            else:
                self.set_state(playback="forward")
        
        self.toggle_play_action.changed.connect(toggle_play)

        @self.state_changed.connect
        def update_toggle_play_action(changes):
            if "playback" in changes:
                is_playing = changes["playback"] in {"forward", "reverse"}
                if is_playing != self.toggle_play_action.isChecked():
                    self.toggle_play_action.blockSignals(True)
                    self.toggle_play_action.setChecked(is_playing)
                    self.toggle_play_action.blockSignals(True)

        clear_cache_action = QAction("clear cache", self)
        clear_cache_action.triggered.connect(lambda: self.set_state(cache=dict()))

        fullscreen_action = QAction("fullscreen", self)
        fullscreen_action.setShortcutContext(Qt.ApplicationShortcut)
        fullscreen_action.triggered.connect(self.toggleFullscreen)
        fullscreen_action.setShortcutContext(Qt.ApplicationShortcut)
        fullscreen_action.setShortcut("u")

        fit_action = QAction("fit", self)
        fit_action.setShortcutContext(Qt.ApplicationShortcut)
        fit_action.setShortcut(QKeySequence(Qt.Key_Backspace))
        fit_action.triggered.connect(self.fit)

        # Menu
        # ----

        ## File menu
        self.menuBar = QMenuBar(self)
        
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

        playback_menu.addAction(set_inpoint_action)
        playback_menu.addAction(set_outpoint_action)

        ## View Menu
        view_menu = self.menuBar.addMenu("View")
        view_menu.addAction(fit_action)
        view_menu.addAction(fullscreen_action)

        ## Window menu
        windows_menu = self.menuBar.addMenu("Windows")

        # show hide windows
        self.show_export_dialog_action = QAction("Export Window")
        self.show_export_dialog_action.setCheckable(True)
        def toggle_export_dialog(val):
            ex = self.state['export']
            ex.update({'visible': val})
            self.set_state(export = ex)

        self.show_export_dialog_action.toggled.connect(toggle_export_dialog)
        windows_menu.addAction(self.show_export_dialog_action)

        @self.state_changed.connect
        def update_export_dialog(changes):
            if 'export' in changes:
                if not self.export_dialog.isVisible() and self.state['export']['filename']:
                    self.export_dialog.show()

                if self.export_dialog.isVisible():
                    self.export_progress.setValue(self.state['export']['progress'])

    # def watch(self, *keys):
    #     pass

    # def on(self, fn):
    #     from inspect import signature
    #     keys = [key for key in signature(fn).parameters] 
    #     print(keys)
    #     relevant_changes = dict()
    #     def on_change(changes):
    #         if any(arg in changes for arg in keys):
    #             args = [changes.get(key) or self.state[key] for key in keys]
    #             fn(*args)
    #             # print(args)
    #             # fn(frame=100, zoom=50)
    #             # wrap(**relevant_changes)
    #             # print("stte changed:", ", ".join(["{}: {}".format(key, val) for key, val in relevant_changes.items()]))

    #     self.state_changed.connect(on_change)

    def create_gui(self):
        # View
        # ----
        self.setLayout(QVBoxLayout())
        self.layout().setContentsMargins(0,0,0,0)
        self.layout().setSpacing(0)

        self.create_menubar()
        self.layout().addWidget(self.menuBar)

        # Widgets
        # ------
        # Viewer toolbar
        viewer_toolbar = QWidget()
        viewer_toolbar.setLayout(QHBoxLayout())

        self.layout().addWidget(viewer_toolbar)

        self.zoom_combo = QComboBox(self)
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
        self.zoom_combo.setFocusPolicy(Qt.ClickFocus)
        self.zoom_combo.currentTextChanged.connect(lambda text: self.set_state(zoom=int(text[:-1])/100 if text[:-1].isnumeric() else text))
        viewer_toolbar.layout().addWidget(self.zoom_combo)
        @self.state_changed.connect
        def update_zoom_combo(changes):
            if 'zoom' in changes:
                zoom_text = "{:.0f}%".format(self.state['zoom']*100) if isinstance(self.state['zoom'], numbers.Number) else self.state['zoom']
                self.zoom_combo.blockSignals(True)
                self.zoom_combo.setCurrentText(zoom_text)
                self.zoom_combo.blockSignals(False)

        downsample_combo = QComboBox()
        downsample_combo.addItems(["Full", "Half", "Quarter"])
        viewer_toolbar.layout().addWidget(downsample_combo)
        @downsample_combo.currentIndexChanged.connect
        def update_downsample(idx):
            self.set_state(downsample=["full", "half", "quarter"][idx])

        @self.state_changed.connect
        def _(changes):
            if 'downsample' in changes:
                idx = ["full", "half", "quarter"].index(changes['downsample'])
                downsample_combo.setCurrentIndex(idx)

        viewer_toolbar.layout().addStretch()

        read_lut_btn = QPushButton("read lut...")
        read_lut_btn.clicked.connect(self.open_lut)
        @self.state_changed.connect
        def _update_lut_btn(change):
            if "lut_path" in change:
                read_lut_btn.setText(change['lut_path'])

        enable_lut_btn = QCheckBox("enable")
        @enable_lut_btn.stateChanged.connect
        def _(checked):
            self.set_state(lut_enabled=checked)

        @self.state_changed.connect
        def _(changes):
            if 'lut_enabled' in changes:
                enable_lut_btn.blockSignals(True)
                enable_lut_btn.setChecked(changes['lut_enabled'])
                enable_lut_btn.blockSignals(False)


        viewer_toolbar.layout().addWidget(read_lut_btn)
        viewer_toolbar.layout().addWidget(enable_lut_btn)
        # Image Viewer
        self.viewer = Viewer2D()
        self.scene = QGraphicsScene()
        self.viewer.setScene(self.scene)
        

        self.pix = QGraphicsPixmapItem()
        self.scene.addItem(self.pix)

        self.resolution_textitem = QGraphicsTextItem()
        self.resolution_textitem.setFlags(QGraphicsItem.ItemIgnoresTransformations) 
        self.scene.addItem(self.resolution_textitem)

        self.viewer.setWrapping(True)
        self.viewer.zoomChanged.connect(lambda: self.set_state(zoom=self.viewer.zoom()))
        @self.viewer.valueChanged.connect
        def scrub_frame(val):
            # wait for current frame to preload when scrubbing
            if self.state['playback'] in {"forward","reverse"}:
                self.set_state(playback="paused")
            self.scrub_event.wait(0.1) # seconds
            self.set_state(frame=val)
        
        @self.state_changed.connect
        def update_viewer_zoom(changes):
            if 'zoom' in changes:
                if changes['zoom'] == "fit":
                    if self.state['image'] is not None:
                        height, width, channels = self.state['image'].shape
                        if self.state['downsample'] == "full":
                            pass
                        elif self.state['downsample'] == "half":
                            width, height = width*2, height*2
                        elif self.state['downsample'] == "quarter":
                            width, height = width*4, height*4
                        else:
                            raise NotImplementedError
                        rect = QRect(0, 0, width, height)

                        self.viewer.fitInView(rect, Qt.KeepAspectRatio)

                elif self.viewer.zoom() != changes['zoom']:
                    if isinstance(changes['zoom'], numbers.Number):
                        self.viewer.blockSignals(True)
                        self.viewer.setZoom(changes['zoom'])
                        self.viewer.blockSignals(False)

            if 'image' in changes and changes['image'] is not None and self.state['zoom'] == "fit":
                height, width, channels = self.state['image'].shape
                if self.state['downsample'] == "full":
                    pass
                elif self.state['downsample'] == "half":
                    width, height = width*2, height*2
                elif self.state['downsample'] == "quarter":
                    width, height = width*4, height*4
                else:
                    raise NotImplementedError
                rect = QRect(0, 0, width, height)
                self.viewer.fitInView(QRect(0, 0, width, height), Qt.KeepAspectRatio)

        @self.state_changed.connect
        def update_viewer_value(changes):
            if 'range' in changes:
                self.viewer.blockSignals(True)
                self.viewer.setMinimum(changes['range'][0])
                self.viewer.setMaximum(changes['range'][1])
                self.viewer.blockSignals(False)

            if 'frame' in changes:
                self.viewer.blockSignals(True)
                self.viewer.setValue(changes['frame'])
                self.viewer.blockSignals(False)

        self.layout().addWidget(self.viewer)

        # Bottom Panel
        # ------------
        time_controls = QWidget()

        time_controls.setLayout(QHBoxLayout())
        time_controls.layout().setContentsMargins(0,0,0,0)
        # time_controls.layout().setSpacing(0)
        self.layout().addWidget(time_controls)

        slider_controls = QFrame(self)
        slider_controls.setLayout(QHBoxLayout())
        slider_controls.layout().setContentsMargins(0,0,0,0)
        slider_controls.layout().setSpacing(0)
        time_controls.layout().addWidget(slider_controls)

        frame_dial = LinearDial()
        frame_dial.setMinimum(-99999)
        frame_dial.setMaximum(99999)
        # frame_dial.setWrapping(True) # seem to crash when?
        frame_dial.setFixedSize(26,26)

        @frame_dial.valueChanged.connect
        def scrub_frame(val):
            # wait for current frame to preload when scrubbing
            if self.state['playback'] in {"forward","reverse"}:
                self.set_state(playback="paused")
            self.scrub_event.wait(0.1) # seconds
            self.set_state(frame=val)

        @self.state_changed.connect
        def update_dial(changes):
            if 'range' in changes:
                frame_dial.blockSignals(True)
                frame_dial.setMinimum(changes['range'][0]-1)
                frame_dial.setMaximum(changes['range'][1]+1)
                frame_dial.blockSignals(False)

            if 'frame' in changes:
                frame_dial.blockSignals(True)
                frame_dial.setValue(changes['frame'])
                frame_dial.blockSignals(False)

        slider_controls.layout().addWidget(frame_dial)

        self.first_frame_spinner = QSpinBox()
        self.first_frame_spinner.setMinimum(-999999)
        self.first_frame_spinner.setMaximum(+999999)
        self.first_frame_spinner.setToolTip("first frame")
        slider_controls.layout().addWidget(self.first_frame_spinner)
        @self.first_frame_spinner.valueChanged.connect
        def update_range(val):
            self.set_state(range=(int(val), self.state['range'][1]))

        @self.state_changed.connect
        def _(changes):
            if 'range' in changes:
                self.first_frame_spinner.blockSignals(True)
                self.first_frame_spinner.setValue(changes['range'][0])
                self.first_frame_spinner.blockSignals(False)

        middle = QWidget()
        middle.setLayout(QVBoxLayout())
        middle.layout().setContentsMargins(16,0,16,0)
        middle.layout().setSpacing(0)
        slider_controls.layout().addWidget(middle)

        # self.range_slider = QRangeSlider(self)
        # self.range_slider.setFixedHeight(5)
        # @self.range_slider.startValueChanged.connect
        # def _(val):
        #     self.set_state(inpoint=val)
# 
        # @self.range_slider.endValueChanged.connect
        # def _(val):
        #     self.set_state(outpoint=val)

        # @self.state_changed.connect
        # def _(changes):
        #     if 'range' in changes:
        #         self.range_slider.blockSignals(True)
        #         self.range_slider.setMinimum(changes['range'][0])
        #         self.range_slider.setMaximum(changes['range'][1])
        #         self.range_slider.blockSignals(False)

        #     if 'inpoint' in changes:
        #         self.range_slider.blockSignals(True)
        #         self.range_slider.setStart(changes['inpoint'])
        #         self.range_slider.blockSignals(False)

        #     if 'outpoint' in changes:
        #         self.range_slider.blockSignals(True)
        #         self.range_slider.setEnd(changes['outpoint'])
        #         self.range_slider.blockSignals(False)

        # middle.layout().addWidget(self.range_slider)

        range_slider = MyRangeSlider()
        range_slider.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        range_slider.setFixedHeight(8)
        @self.state_changed.connect
        def update_range_slider(changes):
            if 'range' in changes:
                range_slider.blockSignals(True)
                range_slider.setMinimum(changes['range'][0])
                range_slider.setMaximum(changes['range'][1])
                range_slider.blockSignals(False)

            if 'inpoint' or 'outpoint' in changes:
                range_slider.blockSignals(True)
                range_slider.setValues(changes.get('inpoint', self.state['inpoint']), changes.get('outpoint', self.state['outpoint']))
                range_slider.blockSignals(False)

        @range_slider.valuesChanged.connect
        def _(v1, v2):
            self.set_state(inpoint=v1, outpoint=v2)

        middle.layout().addWidget(range_slider)
        
        myslider = MySlider(orientation=Qt.Horizontal)
        myslider.setTracking(True)
        middle.layout().addWidget(myslider)
        @myslider.valueChanged.connect
        def scrub_slider(val):
            # wait for current frame to preload when scrubbing
            if self.state['playback'] in {"forward","reverse"}:
                self.set_state(playback="paused")
            self.scrub_event.wait(0.1) # seconds
            self.set_state(frame=val)

        @myslider.rangeChanged.connect
        def _(min, max):
            self.set_state(range=(min, max))

        @self.state_changed.connect
        def _(changes):
            if 'range' in changes:
                myslider.blockSignals(True)
                myslider.setMinimum(changes['range'][0])
                myslider.setMaximum(changes['range'][1])
                myslider.blockSignals(False)

            if 'frame' in changes:
                myslider.blockSignals(True)
                myslider.setValue(changes['frame'])
                myslider.blockSignals(False)

        # self.frame_slider = QSlider(Qt.Horizontal)
        # @self.frame_slider.valueChanged.connect
        # def scrub_slider(val):
        #     # wait for current frame to preload when scrubbing
        #     if self.state['playback'] in {"forward","reverse"}:
        #         self.set_state(playback="paused")
        #     self.scrub_event.wait(0.1) # seconds
        #     self.set_state(frame=val)

        # @self.state_changed.connect
        # def update_slider(changes):
        #     if 'range' in changes:
        #         self.frame_slider.blockSignals(True)
        #         self.frame_slider.setMinimum(changes['range'][0])
        #         self.frame_slider.setMaximum(changes['range'][1])
        #         self.frame_slider.blockSignals(False)

        #     if 'frame' in changes:
        #         self.frame_slider.blockSignals(True)
        #         self.frame_slider.setValue(changes['frame'])
        #         self.frame_slider.blockSignals(False)
        # middle.layout().addWidget(self.frame_slider)
        
        self.cacheBar = CacheBar()
        middle.layout().addWidget(self.cacheBar)

        @self.state_changed.connect
        def update_cachebar(changes):
            if 'range' in changes:
                self.cacheBar.setRange(*changes['range'])
                
            if any(['cache', 'downsample', 'lut_path', 'lut_enabled'] for key in changes):
                downsample = changes.get('downsample', self.state['downsample'])
                lut_path = changes.get('lut_path', self.state['lut_path'])
                lut_enabled = changes.get('lut_enabled', self.state['lut_enabled'])
                lut = lut_path if lut_enabled else None
                cache = changes.get('cache', self.state['cache'])
                cached_frames = [f for (f, s, l) in cache.keys() if s==downsample and l==lut]
                self.cacheBar.setValues(cached_frames)


        self.last_frame_spinner = QSpinBox()
        self.last_frame_spinner.setMinimum(-999999)
        self.last_frame_spinner.setMaximum(+999999)
        self.last_frame_spinner.setToolTip("last frame")
        slider_controls.layout().addWidget(self.last_frame_spinner)
        @self.last_frame_spinner.valueChanged.connect
        def update_last_frame(val):
            self.set_state(range=(self.state['range'][0], int(val)))

        @self.state_changed.connect
        def update_last_frame_spinner(changes):
            if 'range' in changes:
                self.last_frame_spinner.blockSignals(True)
                self.last_frame_spinner.setValue(changes['range'][1])
                self.last_frame_spinner.blockSignals(False)

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
        @self.state_changed.connect
        def update_fps_spinner(changes):
            if 'fps' in changes:
                self.fps_spinner.blockSignals(True)
                self.fps_spinner.setValue(changes['fps'] or 0)
                self.fps_spinner.blockSignals(False)

        playback_controls.layout().addWidget(self.fps_spinner)

        self.skip_to_start_btn = QPushButton("|<<")
        self.skip_to_start_btn.setFixedWidth(26)
        playback_controls.layout().addWidget(self.skip_to_start_btn)
        self.skip_to_start_btn.clicked.connect(lambda: self.set_state(frame=self.state['inpoint']))

        self.step_back_btn = QPushButton("|<")
        self.step_back_btn.setFixedWidth(26)
        playback_controls.layout().addWidget(self.step_back_btn)
        self.step_back_btn.clicked.connect(lambda: self.set_state(frame=self.state['frame']-1))

        self.reverse_btn = QPushButton("\u23F4")
        self.reverse_btn.setFixedWidth(26)
        @self.reverse_btn.clicked.connect
        def toggle_reverse():
            if self.state['playback'] == "reverse":
                self.set_state(playback="paused")
            else:
                self.set_state(playback="reverse")

        @self.state_changed.connect
        def update_reverse_btn(changes):
            if 'playback' in changes:
                if self.state['playback']!="reverse":
                    self.reverse_btn.setText("<")
                else:
                    self.reverse_btn.setText("||")
        playback_controls.layout().addWidget(self.reverse_btn)

        self.frame_spinner = QSpinBox()
        self.frame_spinner.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        self.frame_spinner.setAlignment(Qt.AlignHCenter)
        self.frame_spinner.setStyleSheet("QSpinBox{background-color:transparent}")
        self.frame_spinner.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.frame_spinner.setToolTip("current frame")
        self.frame_spinner.valueChanged.connect(lambda val: self.set_state(frame=val, playback="paused"))
        @self.state_changed.connect
        def update_frame_spinner(changes):
            self.frame_spinner.blockSignals(True)
            if 'range' in changes:
                self.frame_spinner.setMinimum(changes['range'][0])
                self.frame_spinner.setMaximum(changes['range'][1])

            if 'frame' in changes:
                self.frame_spinner.setValue(changes['frame'])
            self.frame_spinner.blockSignals(False)
        playback_controls.layout().addWidget(self.frame_spinner)

        self.forward_btn = QPushButton("\u23F5")
        self.forward_btn.setFixedWidth(26)
        @self.forward_btn.clicked.connect
        def togfle_forward():
            if self.state['playback'] == "forward":
                self.set_state(playback="paused")
            else:
                self.set_state(playback="forward")

        @self.state_changed.connect
        def update_forward_btn(changes):
            if 'playback' in changes:
                if self.state['playback']!="forward":
                    self.forward_btn.setText(">")
                else:
                    self.forward_btn.setText("||")
        playback_controls.layout().addWidget(self.forward_btn)

        self.step_forward_btn = QPushButton(">|")
        self.step_forward_btn.setFixedWidth(26)
        playback_controls.layout().addWidget(self.step_forward_btn)
        self.step_forward_btn.clicked.connect(lambda: self.set_state(frame=self.state['frame']+1))

        self.skip_to_end_btn = QPushButton(">>|")
        self.skip_to_end_btn.setFixedWidth(26)
        playback_controls.layout().addWidget(self.skip_to_end_btn)
        self.skip_to_end_btn.clicked.connect(lambda: self.set_state(frame=self.state['outpoint']))

        for btn in [self.skip_to_start_btn, self.step_back_btn, self.reverse_btn, self.forward_btn, self.step_forward_btn, self.skip_to_end_btn]:
            btn.setFlat(True)

        # playback_controls.layout().addStretch()

        self.fps_label = QLabel("fps")
        self.fps_label.setFixedWidth(30)
        # bottom.layout().addWidget(self.fps_label)

        self.oscilloscope = Oscilloscope()
        self.oscilloscope.setMinimum(0)
        self.oscilloscope.setMaximum(2/self.state['fps'])

        self.oscilloscope.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        self.oscilloscope.resize(100,10)

        @self.state_changed.connect
        def update_oscilloscope(changes):
            if 'fps' in changes:
                self.oscilloscope.setMaximum(2/changes['fps'] if changes['fps'] else 120)

        self.statusbar = QStatusBar()
        self.layout().addWidget(self.statusbar)

        self.system_memory_label = QLabel("system memory")
        self.statusbar.addPermanentWidget(self.system_memory_label)
        @self.state_changed.connect
        def update_system_memory_label(changes):
            if 'cache' in changes:
                total_memory = psutil.virtual_memory().total / (1024.0 ** 3)
                available_memory = psutil.virtual_memory().available / (1024.0 ** 3)
                system_memory_text = "system: {:.2f}/{:.2f}GB ".format(available_memory, total_memory)

                self.system_memory_label.setText(system_memory_text)

        self.path_label = QLabel()
        self.statusbar.addPermanentWidget(self.path_label)
        @self.state_changed.connect
        def _(changes):
            if 'path' in changes:
                self.path_label.setText(changes['path'])

        # memory
        self.memory_label = QLabel("memory")
        @self.state_changed.connect
        def _(changes):
            if 'memory' in changes:
                memory_text = "{:.0f}MB /".format(self.state['memory'])
                self.memory_label.setText(memory_text)

        # self.memory_label.setFixedWidth(100)
        self.memory_spinner = QSpinBox()
        self.memory_spinner.setStyleSheet("QSpinBox{background-color:transparent}")
        self.memory_spinner.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.memory_spinner.setSuffix("MB")
        self.memory_spinner.setFrame(False)
        self.memory_spinner.valueChanged.connect(lambda val: self.set_state(memory_limit=val))
        self.memory_spinner.setMinimum(0)
        self.memory_spinner.setMaximum(99999)
        self.memory_spinner.setValue(self.state['memory_limit'])
        @self.state_changed.connect
        def _(changes):
            if 'memory_limit' in changes:
                self.memory_spinner.blockSignals(True)
                self.memory_spinner.setValue(changes['memory_limit'])
                self.memory_spinner.blockSignals(False)

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
        self.timer.setTimerType(Qt.PreciseTimer)

        def next_frame():
            left = max(self.state['inpoint'], self.state['range'][0])
            right = min(self.state['outpoint'], self.state['range'][1])

            if self.state['playback'] == "forward":
                frame = self.state['frame']+1
                if frame>right:
                    frame = left

            elif self.state["playback"] == "reverse":
                frame = self.state['frame']-1
                if frame<left:
                    frame = right

            self.set_state(frame=frame)

        self.timer.timeout.connect(next_frame)
        # update timer interval based on fps
        # @self.state_changed.connect
        # def update_timer(changes):
        #     if any(key in changes for key in ['fps', 'playback', 'cache']):
        #         playback = changes.get('playback', self.state['playback'])
        #         fps = changes.get('fps', self.state['fps'])
        #         cache = changes.get('cache', self.state['cache'])
        #         print(changes.get('frame'))
        #         frame = changes.get('frame', self.state['frame'])
        #         print(frame, self.state['frame'])

        #         interval = 1000/fps if fps else 0
        #         if self.timer.interval() != interval:
        #             self.timer.setInterval(interval)

        #         # start/stop timer
        #         if playback in {"forward", "reverse"}:
        #             if frame not in cache:
        #                 if self.timer.isActive():
        #                     self.timer.stop()

        #             if frame in cache:
        #                 if not self.timer.isActive():
        #                     self.timer.start(1000/fps if fps else 0)

        #         elif self.state['playback'] == "paused":
        #             if self.timer.isActive():
        #                 self.timer.stop()

        self.dialog = QDialog(self)
        self.dialog.setLayout(QVBoxLayout())



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
        IsNewImage = self.state['image'] is not None and self._image_buffer is not self.state['image']
        
        if IsNewImage:
            self._image_buffer = self.state['image']
            self._image_buffer.flags.writeable = False
            # IsEqual = str(self._image_buffer) == str(self.state['image'])
            # IsSame = self._image_buffer is self.state['image']
            # print( IsSame, IsEqual)

        # update gui


        # if self.state['export']['filename'] and not self.export_dialog.isVisible():
        #     if self.export_dialog
        #     self.export_dialog.show()

        # else:
        #     self.export_dialog.hide()

        # if self.path_label.text() != self.state['path']:
        #     self.path_label.setText(self.state['path'])

        # if self.fps_spinner.value() != self.state['fps']:
        #     self.fps_spinner.blockSignals(True)
        #     self.fps_spinner.setValue(self.state['fps'] or 0)
        #     self.fps_spinner.blockSignals(False)

        # if self.memory_spinner.value() != self.state['memory_limit']:
        #     self.memory_spinner.blockSignals(True)
        #     self.memory_spinner.setValue(self.state['memory_limit'])
        #     self.memory_spinner.blockSignals(False)

        # if self.frame_slider.value() != self.state['frame']:
        #     self.frame_slider.blockSignals(True)
        #     self.frame_slider.setValue(self.state['frame'])
        #     self.frame_slider.blockSignals(False)

        # if (self.frame_slider.minimum(), self.frame_slider.maximum()) != self.state['range']:
        #     self.frame_slider.blockSignals(True)
        #     self.frame_slider.setMinimum(self.state['range'][0])
        #     self.frame_slider.setMaximum(self.state['range'][1])
        #     self.frame_slider.blockSignals(False)

        # if self.frame_spinner.value() != self.state['frame']:
        #     self.frame_spinner.blockSignals(True)
        #     self.frame_spinner.setValue(self.state['frame'])
        #     self.frame_spinner.blockSignals(False)

        # if (self.frame_spinner.minimum(), self.frame_spinner.maximum()) != self.state['range']:
        #     self.frame_spinner.blockSignals(True)
        #     self.frame_spinner.setMinimum(self.state['range'][0])
        #     self.frame_spinner.setMaximum(self.state['range'][1])
        #     self.frame_spinner.blockSignals(False)

        # if self.first_frame_spinner.value() != self.state['range'][0]:
        #     self.first_frame_spinner.blockSignals(True)
        #     self.first_frame_spinner.setValue(self.state['range'][0])
        #     self.first_frame_spinner.blockSignals(False)

        # if self.last_frame_spinner.value() != self.state['range'][1]:
        #     self.last_frame_spinner.blockSignals(True)
        #     self.last_frame_spinner.setValue(self.state['range'][1])
        #     self.last_frame_spinner.blockSignals(False)

        # if self.cacheBar.range() != self.state['range']:
        #     self.cacheBar.setRange(*self.state['range'])
            
        # if self.cacheBar.values() != self.state['cache'].keys():
        #     self.cacheBar.setValues([val for val in self.state['cache'].keys() ])

        # if self.state["playback"] == "forward":
        #     if not self.pause_btn.isVisible():
        #         self.pause_btn.setVisible(True)
        #     if self.forward_btn.isVisible():
        #         self.forward_btn.setVisible(False)
        # else:
        #     if self.pause_btn.isVisible():
        #         self.pause_btn.setVisible(False)
        #     if not self.forward_btn.isVisible():
        #         self.forward_btn.setVisible(True)

        # if self.state["playback"] == "reverse":
        #     if not self.reverse_pause_btn.isVisible():
        #         self.reverse_pause_btn.setVisible(True)
        #     if self.reverse_btn.isVisible():
        #         self.reverse_btn.setVisible(False)
        # else:
        #     if self.reverse_pause_btn.isVisible():
        #         self.reverse_pause_btn.setVisible(False)
        #     if not self.reverse_btn.isVisible():
        #         self.reverse_btn.setVisible(True)

        # high = self.state['fps']*2 if self.state['fps'] else 120
        # if self.oscilloscope.maximum() != high:
        #     self.oscilloscope.setMaximum(high)

        if IsNewImage:
            # update viewer image
            height, width, channel = self.state['image'].shape
            bytesPerLine = 3 * width
            qImg = QImage(self.state['image'].data, width, height, bytesPerLine, QImage.Format_RGB888)
            scale = 1
        
            if self.state['downsample'] == 'half':
                scale = 2
            elif self.state['downsample'] == 'quarter':
                scale = 4

            pixmap = QPixmap(qImg).scaled(int(width*scale), int(height*scale), Qt.IgnoreAspectRatio)
            self.pix.setPixmap(pixmap)


            # update resolution label
            self.resolution_label.setText("{}x{}".format(width*scale, height*scale))
            self.resolution_textitem.setPos(width*scale, height*scale)
            self.resolution_textitem.setPlainText("{}x{}".format(width*scale, height*scale))

        # if self.state['zoom'] == "fit":
        #     self.viewer.fitInView(self.pix.boundingRect(), Qt.KeepAspectRatio)

        # elif self.viewer.zoom() != self.state['zoom']:
        #     # print("change zoom:", self.viewer.zoom(), self.state['zoom'])
        #     if isinstance(self.state['zoom'], numbers.Number):
        #         self.viewer.blockSignals(True)
        #         self.viewer.setZoom(self.state['zoom'])
        #         self.viewer.blockSignals(False)

        # memory_text = "{:.0f}MB /".format(self.state['memory'])
        # if self.memory_label.text() != memory_text:
        #     self.memory_label.setText(memory_text)

        # zoom_text = "{:.0f}%".format(self.state['zoom']*100) if isinstance(self.state['zoom'], numbers.Number) else self.state['zoom']
        # if self.zoom_combo.currentText() != zoom_text:
        #     self.zoom_combo.blockSignals(True)
        #     self.zoom_combo.setCurrentText(zoom_text)
        #     self.zoom_combo.blockSignals(False)

        # total_memory = psutil.virtual_memory().total / (1024.0 ** 3)
        # available_memory = psutil.virtual_memory().available / (1024.0 ** 3)
        # system_memory_text = "system: {:.2f}/{:.2f}GB ".format(available_memory, total_memory)
        # if self.system_memory_label.text() != system_memory_text:
        #     self.system_memory_label.setText(system_memory_text)

        if IsNewImage:
            # update fps counter
            timestamp = datetime.now()
            if self.last_timestamp:
                dt = (timestamp-self.last_timestamp).total_seconds()
                if dt>0:
                    self.fps_label.setText("{:.2f}".format(1/dt))
                    times = [v for v in self.times.values()]+[dt]
                    self.oscilloscope.push(*times)

            self.last_timestamp = timestamp

        # watch playback and start or stop timer
        # redundant see later
        interval = int(1000/self.state['fps']) if self.state['fps'] else 0
        self.statusbar.showMessage(f"{1000/interval if interval>0 else 'inf'}")
        if self.state['playback'] in {"forward", "reverse"}:
            if not self.timer.isActive():
                print("restart timer!", datetime.now())
                self.timer.start(interval)

        if self.state['playback'] == "paused" and self.timer.isActive():
            print("pause timer", datetime.now())
            self.timer.stop()

        # update timer interval based on fps
        
        if self.timer.interval() != interval:
            self.timer.setInterval(interval)

        # start/stop timer
        if self.state['playback'] in {"forward", "reverse"}:
            frame = self.state['frame']
            downsample = self.state['downsample']
            lut_path = self.state['lut_path']
            lut_enabled = self.state['lut_enabled']
            lut = lut_path if lut_enabled else None
            if (frame, downsample, lut) not in self.state['cache']:
                if self.timer.isActive():
                    print("pause timer 2")

                    self.timer.stop()

            if (frame, downsample, lut) in self.state['cache']:
                if not self.timer.isActive():
                    self.timer.start(interval)

        elif self.state['playback'] == "paused":
            if self.timer.isActive():
                print("stop timer 2")
                self.timer.stop()

    def resizeEvent(self, event):
        # uodate viewer
        if self.state['zoom'] == "fit":
            self.fit()

    def closeEvent(self, event):
        self.running = False
        print("close")

def main():
    import sys
    from widgets.themes import apply_dark_theme2
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

    window.open_lut("../tests/resources/AlexaV3_K1S1_LogC2Video_Rec709_EE_aftereffects3d.cube")
    window.open("../tests/resources/MASA_sequence/MASA_sequence_00196.jpg")
    # window.open("../tests/resources/EF_VFX_04/EF_VFX_04_0094900.dpx")
    
    window.set_state(fps=24, memory_limit=1000)
    app.exec_()

if __name__ == "__main__":
    main()