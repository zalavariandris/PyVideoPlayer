
# python packages
import time
import threading
from pathlib import Path

# import os
import numbers
import mimetypes

# third party
import numpy as np
import cv2
import psutil

import OpenImageIO as oiio

from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

# widgets
from widgets.viewer2D import Viewer2D
from widgets.myslider import MySlider # for the frameslider
from widgets.myrangeslider import MyRangeSlider # for the frame range slider
from widgets.lineardial import LinearDial # for the frame dial
from widgets.cachebar import CacheBar
from widgets.oscilloscope import Oscilloscope

# utils
from read import Reader
from invoke_in_main import inmain_later, inmain_decorator
from LUT import read_lut, apply_lut

from dataclasses import dataclass


from frame_server import FrameServer, ProcessDesc


class Viewer2D(Viewer2D):
    """on righh mouse drag viewer acts as a frame dial"""
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


class VideoPlayer(QWidget):
    state_changed = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.state = {
            'path': None,
            'fps': 24,
            'frame': 0,
            'range': [0, 100],
            'inpoint': 0,
            'outpoint': 100,
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
            'used_memory': 0,
        }

        # Create and binf frameserver
        # ---------------------------
        self.frame_server = FrameServer()
        # watch changes to request frames
        @self.state_changed.connect
        def request_frame_on_change(changes):
            if any(key in changes for key in ['frame', 'path', 'downsample', 'lut_enabled', 'lut_path']):
                key = self.make_key()
                if key.is_valid():
                    self.frame_server.request_frame(self.make_key())

        @self.frame_server.frame_done.connect
        def update_image_state(key):
            # print("frame done:", key)
            if key == self.make_key():
                pixels = self.frame_server[key]
                if pixels is not None:
                    self.set_state(image=pixels)

        @self.frame_server.cache_changed.connect
        def update_used_memory():
            self.set_state(used_memory=self.frame_server.used_memory())

        # init gui
        self.init_gui()

    # STATE

    # @inmain_decorator(wait_for_return=False)
    def set_state(self, **kwargs):
        # print("set state", kwargs.keys())
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


            changes['zoom'] = "fit"


        # if "lut_path" in changes:
        #     self._lut = read_lut(changes['lut_path'])

        if 'memory_limit' in changes:
            self.frame_server.memory_limit = changes['memory_limit']

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

            # if key not in self.frame_server._cache:
            #     self.frame_server.set_requested_frames([key])
            # else:
            #     pixels, timestamp = self.frame_server._cache[key]
            #     changes['image'] = pixels

        # # compute 'image'
        # if any(['frame', 'path', 'cache', 'downsample', 'lut_enabled', 'lut_path'] for key in changes):
        #     frame = changes.get('frame', self.state['frame'])
        #     downsample = self.state['downsample']
        #     lut_path = changes.get('lut_path', self.state['lut_path'])
        #     lut_enabled = changes.get('lut_enabled', self.state['lut_enabled'])
        #     lut = lut_path if lut_enabled else None
        #     if (frame, downsample, lut) in self._cache:
        #         image, _ = self._cache[(frame, downsample, lut)]
        #     else:
        #         image = None

        #     changes['image'] = image

        # # compute 'memory'
        # if "cache" in changes:
        #     cache = changes.get('cache', self.state['cache'])
        #     megabytes = 0
        #     for (frame, downsample, lut), (image, timestamp) in cache.items():
        #         megabytes+=image.nbytes / 1024 / 1024 # in MB
        #     changes['memory'] = megabytes

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

    def make_key(self):
        path = self.state['path']
        frame = self.state['frame']
        downsample = self.state['downsample']
        lut_path = self.state['lut_path']
        lut_enabled = self.state['lut_enabled']
        lut = lut_path if lut_enabled else None
        key = (frame, downsample, lut)

        desc = ProcessDesc(path=path, frame=frame, downsample=downsample, lut=lut)
        return desc
        return desc if desc.is_valid() else None

    # GUI

    def create_menubar(self)->QMenuBar:
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
        
        toggle_play_action = QAction("toggle_play", self)
        toggle_play_action.setCheckable(True)
        toggle_play_action.setShortcutContext(Qt.ApplicationShortcut)
        toggle_play_action.setShortcut(QKeySequence(Qt.Key_Space))

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
        
        toggle_play_action.changed.connect(toggle_play)

        @self.state_changed.connect
        def update_toggle_play_action(changes):
            if "playback" in changes:
                is_playing = changes["playback"] in {"forward", "reverse"}
                if is_playing != toggle_play_action.isChecked():
                    toggle_play_action.blockSignals(True)
                    toggle_play_action.setChecked(is_playing)
                    toggle_play_action.blockSignals(True)

        clear_cache_action = QAction("clear cache", self)
        clear_cache_action.triggered.connect(lambda: self.frame_server.clear_cache())

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
        menubar = QMenuBar(self)
        
        fileMenu = menubar.addMenu("File")

        fileMenu.addAction(openAction)
        fileMenu.addAction(exportAction)
        fileMenu.addAction(quitAction)

        ## Playback Menu
        playback_menu = menubar.addMenu("Playback")
        playback_menu.addAction(reverse_action)
        playback_menu.addAction(forward_action)
        playback_menu.addAction(pause_action)
        playback_menu.addAction(toggle_play_action)
        playback_menu.addAction(clear_cache_action)

        playback_menu.addAction(set_inpoint_action)
        playback_menu.addAction(set_outpoint_action)

        ## View Menu
        view_menu = menubar.addMenu("View")
        view_menu.addAction(fit_action)
        view_menu.addAction(fullscreen_action)

        ## Window menu
        windows_menu = menubar.addMenu("Windows")

        # show hide windows
        show_export_dialog_action = QAction("Export Window")
        show_export_dialog_action.setCheckable(True)
        def toggle_export_dialog(val):
            ex = self.state['export']
            ex.update({'visible': val})
            self.set_state(export = ex)

        show_export_dialog_action.toggled.connect(toggle_export_dialog)
        windows_menu.addAction(show_export_dialog_action)

        @self.state_changed.connect
        def update_export_dialog(changes):
            if 'export' in changes:
                if not self.export_dialog.isVisible() and self.state['export']['filename']:
                    self.export_dialog.show()

                if self.export_dialog.isVisible():
                    self.export_progress.setValue(self.state['export']['progress'])

        return menubar

    def create_image_toolbar(self)->QWidget:
        # Create Image Toolbar
        # ====================
        image_toolbar = QWidget()
        image_toolbar.setLayout(QHBoxLayout())
        

        # zoom control
        zoom_combo = QComboBox(self)
        zoom_combo.setToolTip("zoom")
        zoom_combo.addItem("fit")
        zoom_combo.addItem("10%")
        zoom_combo.addItem("25%")
        zoom_combo.addItem("50%")
        zoom_combo.addItem("100%")
        zoom_combo.addItem("200%")
        zoom_combo.addItem("400%")
        zoom_combo.addItem("800%")
        zoom_combo.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        zoom_combo.setEditable(True)
        zoom_combo.setFocusPolicy(Qt.ClickFocus)
        zoom_combo.currentTextChanged.connect(lambda text: self.set_state(zoom=int(text[:-1])/100 if text[:-1].isnumeric() else text))
        image_toolbar.layout().addWidget(zoom_combo)

        @self.state_changed.connect
        def update_zoom_combo(changes):
            if 'zoom' in changes:
                zoom_text = "{:.0f}%".format(self.state['zoom']*100) if isinstance(self.state['zoom'], numbers.Number) else self.state['zoom']
                zoom_combo.blockSignals(True)
                zoom_combo.setCurrentText(zoom_text)
                zoom_combo.blockSignals(False)

        # downsample control
        downsample_combo = QComboBox()
        downsample_combo.addItems(["Full", "Half", "Quarter"])
        image_toolbar.layout().addWidget(downsample_combo)
        @downsample_combo.currentIndexChanged.connect
        def update_downsample(idx):
            self.set_state(downsample=["full", "half", "quarter"][idx])

        @self.state_changed.connect
        def _(changes):
            if 'downsample' in changes:
                idx = ["full", "half", "quarter"].index(changes['downsample'])
                downsample_combo.setCurrentIndex(idx)

        image_toolbar.layout().addStretch()

        # lut controls
        read_lut_btn = QPushButton("read lut...")
        read_lut_btn.clicked.connect(self.open_lut)
        @self.state_changed.connect
        def update_lut_btn(change):
            if "lut_path" in change:
                path = change['lut_path']
                name = Path(path).stem
                read_lut_btn.setText(name)
                read_lut_btn.setToolTip(path)
        image_toolbar.layout().addWidget(read_lut_btn)

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
        image_toolbar.layout().addWidget(enable_lut_btn)

        return image_toolbar

    def create_image_viewer(self):
        # Create Image Viewer
        # ===================
        image_viewer = Viewer2D()
        image_scene = QGraphicsScene()
        image_viewer.setScene(image_scene)
        
        # the image pixmap
        pixitem = QGraphicsPixmapItem()
        image_scene.addItem(pixitem)

        @self.state_changed.connect
        def sync_pixmap(changes):
            if 'image' in changes:
                pixels = self.frame_server[self.make_key()]
                if pixels is None:
                    print("empty stuff")
                    return
                # update viewer image
                height, width, channel = pixels.shape
                bytesPerLine = 3 * width
                qImg = QImage(pixels.data, width, height, bytesPerLine, QImage.Format_RGB888)
                scale = 1
            
                if self.state['downsample'] == 'half':
                    scale = 2
                elif self.state['downsample'] == 'quarter':
                    scale = 4

                pixmap = QPixmap(qImg).scaled(int(width*scale), int(height*scale), Qt.IgnoreAspectRatio)
                pixitem.setPixmap(pixmap)

        # display resolution in the bottom right corner
        resolution_textitem = QGraphicsTextItem()
        resolution_textitem.setFlags(QGraphicsItem.ItemIgnoresTransformations) 
        image_scene.addItem(resolution_textitem)

        @self.state_changed.connect
        def sync_resolution_label(changes):
            if 'image' in changes:
                if changes['image'] is None:
                    return
                    
                height, width, channels = changes['image'].shape

                # compensate display size
                scale = 1
                if self.state['downsample'] == 'half':
                    scale = 2
                elif self.state['downsample'] == 'quarter':
                    scale = 4

                resolution_textitem.setPlainText("{}x{}".format(width*scale, height*scale))
                resolution_textitem.setPos(width*scale, height*scale)
                resolution_textitem.setPlainText("{}x{}".format(width*scale, height*scale))

        image_viewer.zoomChanged.connect(lambda: self.set_state(zoom=image_viewer.zoom()))
        
        @self.state_changed.connect
        def sync_viewer_zoom(changes):
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

                        image_viewer.fitInView(rect, Qt.KeepAspectRatio)

                elif image_viewer.zoom() != changes['zoom']:
                    if isinstance(changes['zoom'], numbers.Number):
                        image_viewer.blockSignals(True)
                        image_viewer.setZoom(changes['zoom'])
                        image_viewer.blockSignals(False)

        @self.state_changed.connect
        def fit_when_image_changed(changes):
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
                image_viewer.fitInView(QRect(0, 0, width, height), Qt.KeepAspectRatio)

        # connect viewer as a framedial to scrub with rightmouse button
        image_viewer.setWrapping(True)
        @image_viewer.valueChanged.connect
        def scrub_frame(val):
            # wait for current frame to preload when scrubbing
            if self.state['playback'] in {"forward","reverse"}:
                self.set_state(playback="paused")
            # self.scrub_event.wait(0.1) # seconds
            self.set_state(frame=val)

        @self.state_changed.connect
        def sync_viewer_value(changes):
            if 'range' in changes:
                image_viewer.blockSignals(True)
                image_viewer.setMinimum(changes['range'][0])
                image_viewer.setMaximum(changes['range'][1])
                image_viewer.blockSignals(False)

            if 'frame' in changes:
                image_viewer.blockSignals(True)
                image_viewer.setValue(changes['frame'])
                image_viewer.blockSignals(False)

        return image_viewer

    def create_time_controls(self)->QWidget:
        # Create Time Controls (frame slider and playback controls)
        # --------------------------------------------------------
        time_controls = QWidget()
        time_controls.setLayout(QHBoxLayout())
        time_controls.layout().setContentsMargins(0,0,0,0)
        # time_controls.layout().setSpacing(0)

        # Create Slider Controls
        # ======================
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
            # self.scrub_event.wait(0.1) # seconds
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

        first_frame_spinner = QSpinBox()
        first_frame_spinner.setMinimum(-999999)
        first_frame_spinner.setMaximum(+999999)
        first_frame_spinner.setToolTip("first frame")
        slider_controls.layout().addWidget(first_frame_spinner)
        @first_frame_spinner.valueChanged.connect
        def update_range(val):
            self.set_state(range=(int(val), self.state['range'][1]))

        @self.state_changed.connect
        def _(changes):
            if 'range' in changes:
                first_frame_spinner.blockSignals(True)
                first_frame_spinner.setValue(changes['range'][0])
                first_frame_spinner.blockSignals(False)

        middle = QWidget()
        middle.setLayout(QVBoxLayout())
        middle.layout().setContentsMargins(16,0,16,0)
        middle.layout().setSpacing(0)
        slider_controls.layout().addWidget(middle)

        frame_range_slider = MyRangeSlider()
        frame_range_slider.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        frame_range_slider.setFixedHeight(8)
        @self.state_changed.connect
        def update_range_slider(changes):
            if 'range' in changes:
                frame_range_slider.blockSignals(True)
                frame_range_slider.setMinimum(changes['range'][0])
                frame_range_slider.setMaximum(changes['range'][1])
                frame_range_slider.blockSignals(False)

            if 'inpoint' or 'outpoint' in changes:
                frame_range_slider.blockSignals(True)
                frame_range_slider.setValues(changes.get('inpoint', self.state['inpoint']), changes.get('outpoint', self.state['outpoint']))
                frame_range_slider.blockSignals(False)

        @frame_range_slider.valuesChanged.connect
        def _(v1, v2):
            self.set_state(inpoint=v1, outpoint=v2)

        middle.layout().addWidget(frame_range_slider)
        
        frame_slider = MySlider(orientation=Qt.Horizontal)
        frame_slider.setTracking(True)
        middle.layout().addWidget(frame_slider)
        @frame_slider.valueChanged.connect
        def scrub_slider(val):
            # wait for current frame to preload when scrubbing
            if self.state['playback'] in {"forward","reverse"}:
                self.set_state(playback="paused")
            self.set_state(frame=val)
            # self.frame_server.wait_for_frame(self.make_key(), 1/8)

        @frame_slider.rangeChanged.connect
        def _(min, max):
            self.set_state(range=(min, max))

        @self.state_changed.connect
        def _(changes):
            if 'range' in changes:
                frame_slider.blockSignals(True)
                frame_slider.setMinimum(changes['range'][0])
                frame_slider.setMaximum(changes['range'][1])
                frame_slider.blockSignals(False)

            if 'frame' in changes:
                frame_slider.blockSignals(True)
                frame_slider.setValue(changes['frame'])
                frame_slider.blockSignals(False)
        
        cacheBar = CacheBar()
        middle.layout().addWidget(cacheBar)

        @self.state_changed.connect
        def update_cachebar(changes):
            if 'range' in changes:
                cacheBar.setRange(*changes['range'])
                
            if any(['downsample', 'lut_path', 'lut_enabled'] for key in changes):
                downsample = changes.get('downsample', self.state['downsample'])
                lut_path = changes.get('lut_path', self.state['lut_path'])
                lut_enabled = changes.get('lut_enabled', self.state['lut_enabled'])
                lut = lut_path if lut_enabled else None
                cached_frames = [key.frame for key in self.frame_server if key.downsample==downsample and key.lut==lut]
                cacheBar.setValues(cached_frames)



        # Create playback controls
        # ========================
        playback_controls = QWidget()
        playback_controls.setLayout(QHBoxLayout())
        playback_controls.layout().setContentsMargins(0,0,0,0)
        playback_controls.layout().setSpacing(0)
        time_controls.layout().addWidget(playback_controls)

        last_frame_spinner = QSpinBox()
        last_frame_spinner.setMinimum(-999999)
        last_frame_spinner.setMaximum(+999999)
        last_frame_spinner.setToolTip("last frame")
        slider_controls.layout().addWidget(last_frame_spinner)
        @last_frame_spinner.valueChanged.connect
        def update_last_frame(val):
            self.set_state(range=(self.state['range'][0], int(val)))

        @self.state_changed.connect
        def update_last_frame_spinner(changes):
            if 'range' in changes:
                last_frame_spinner.blockSignals(True)
                last_frame_spinner.setValue(changes['range'][1])
                last_frame_spinner.blockSignals(False)

        fps_spinner = QSpinBox()
        fps_spinner.setToolTip("fps")
        fps_spinner.setSuffix("fps")
        fps_spinner.valueChanged.connect(lambda val: self.set_state(fps=val))
        @self.state_changed.connect
        def update_fps_spinner(changes):
            if 'fps' in changes:
                fps_spinner.blockSignals(True)
                fps_spinner.setValue(changes['fps'] or 0)
                fps_spinner.blockSignals(False)

        playback_controls.layout().addWidget(fps_spinner)

        skip_to_start_btn = QPushButton("|<<")
        skip_to_start_btn.setFixedWidth(26)
        playback_controls.layout().addWidget(skip_to_start_btn)
        skip_to_start_btn.clicked.connect(lambda: self.set_state(frame=self.state['inpoint']))

        step_back_btn = QPushButton("|<")
        step_back_btn.setFixedWidth(26)
        playback_controls.layout().addWidget(step_back_btn)
        step_back_btn.clicked.connect(lambda: self.set_state(frame=self.state['frame']-1))

        reverse_btn = QPushButton("\u23F4")
        reverse_btn.setFixedWidth(26)
        @reverse_btn.clicked.connect
        def toggle_reverse():
            if self.state['playback'] == "reverse":
                self.set_state(playback="paused")
            else:
                self.set_state(playback="reverse")

        @self.state_changed.connect
        def update_reverse_btn(changes):
            if 'playback' in changes:
                if self.state['playback']!="reverse":
                    reverse_btn.setText("<")
                else:
                    reverse_btn.setText("||")
        playback_controls.layout().addWidget(reverse_btn)

        frame_spinner = QSpinBox()
        frame_spinner.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        frame_spinner.setAlignment(Qt.AlignHCenter)
        frame_spinner.setStyleSheet("QSpinBox{background-color:transparent}")
        frame_spinner.setButtonSymbols(QAbstractSpinBox.NoButtons)
        frame_spinner.setToolTip("current frame")
        frame_spinner.valueChanged.connect(lambda val: self.set_state(frame=val, playback="paused"))
        @self.state_changed.connect
        def update_frame_spinner(changes):
            frame_spinner.blockSignals(True)
            if 'range' in changes:
                frame_spinner.setMinimum(changes['range'][0])
                frame_spinner.setMaximum(changes['range'][1])

            if 'frame' in changes:
                frame_spinner.setValue(changes['frame'])
            frame_spinner.blockSignals(False)
        playback_controls.layout().addWidget(frame_spinner)

        forward_btn = QPushButton("\u23F5")
        forward_btn.setFixedWidth(26)
        @forward_btn.clicked.connect
        def togfle_forward():
            if self.state['playback'] == "forward":
                self.set_state(playback="paused")
            else:
                self.set_state(playback="forward")

        @self.state_changed.connect
        def update_forward_btn(changes):
            if 'playback' in changes:
                if self.state['playback']!="forward":
                    forward_btn.setText(">")
                else:
                    forward_btn.setText("||")
        playback_controls.layout().addWidget(forward_btn)

        step_forward_btn = QPushButton(">|")
        step_forward_btn.setFixedWidth(26)
        playback_controls.layout().addWidget(step_forward_btn)
        step_forward_btn.clicked.connect(lambda: self.set_state(frame=self.state['frame']+1))

        skip_to_end_btn = QPushButton(">>|")
        skip_to_end_btn.setFixedWidth(26)
        playback_controls.layout().addWidget(skip_to_end_btn)
        skip_to_end_btn.clicked.connect(lambda: self.set_state(frame=self.state['outpoint']))

        for btn in [skip_to_start_btn, step_back_btn, reverse_btn, forward_btn, step_forward_btn, skip_to_end_btn]:
            btn.setFlat(True)

        return time_controls

    def create_statusbar(self)->QStatusBar:
        # Create The Statusbar
        # ====================
        statusbar = QStatusBar()
        self.layout().addWidget(statusbar)

        fps_label = QLabel("fps")
        fps_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        fps_label.setFixedWidth(30)
        timestamp = time.time()

        @self.state_changed.connect
        def calc_fps(changes):
            nonlocal timestamp
            if 'image' in changes and changes['image'] is not None:
                dt = time.time() - timestamp
                if dt>0:
                    fps_label.setText("{:.0f}fps".format(1/dt if dt else 'inf'))
                timestamp = time.time()

        oscilloscope = Oscilloscope(legend = ['read', 'resize', 'lut'], format="{name}: {value:.3f}s")
        oscilloscope._stack = True

        oscilloscope.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        oscilloscope.resize(100,10)

        @self.state_changed.connect
        def update_oscilloscope(changes):
            if 'image' in changes and changes['image'] is not None:
                # print("-profile-")
                # for key, t in self.frame_server.times.items():
                #     print("{:<10} {:.3f}s".format( key+":", t) )
                # print()
                oscilloscope.push(*[t for t in self.frame_server.times.values()])

        # Create memory widget
        memory_widget = QWidget()
        memory_widget.setLayout(QHBoxLayout())

        # create system memory widget
        system_memory_label = QLabel("system memory")
        statusbar.addPermanentWidget(system_memory_label)

        @self.frame_server.cache_changed.connect
        def update_system_memory_label():
            total_memory = psutil.virtual_memory().total / (1024.0 ** 3)
            available_memory = psutil.virtual_memory().available / (1024.0 ** 3)
            system_memory_text = "system: {:.2f}/{:.2f}GB ".format(available_memory, total_memory)

            system_memory_label.setText(system_memory_text)

        memory_label = QLabel("memory")
        @self.state_changed.connect
        def sync_memory_label(changes):
            if 'used_memory' in changes:
                memory_text = "{:.0f}MB /".format(self.state['used_memory'])
                memory_label.setText(memory_text)

        memory_spinner = QSpinBox()
        memory_spinner.setStyleSheet("QSpinBox{background-color:transparent}")
        memory_spinner.setButtonSymbols(QAbstractSpinBox.NoButtons)
        memory_spinner.setSuffix("MB")
        memory_spinner.setFrame(False)
        memory_spinner.valueChanged.connect(lambda val: self.set_state(memory_limit=val))
        memory_spinner.setMinimum(0)
        memory_spinner.setMaximum(99999)
        memory_spinner.setValue(self.state['memory_limit'])
        @self.state_changed.connect
        def _(changes):
            if 'memory_limit' in changes:
                memory_spinner.blockSignals(True)
                memory_spinner.setValue(changes['memory_limit'])
                memory_spinner.blockSignals(False)

        memory_widget = QWidget()
        memory_widget.setLayout(QHBoxLayout())
        memory_widget.layout().addWidget(system_memory_label)
        memory_widget.layout().addWidget(memory_label)
        memory_widget.layout().addWidget(memory_spinner)
        memory_widget.layout().setContentsMargins(0,0,0,0)
        memory_widget.layout().setSpacing(0)
        statusbar.addPermanentWidget(memory_widget)

        # add resolution label to statusbar
        resolution_label = QLabel("resolution")

        @self.state_changed.connect
        def sync_resolution_label(changes):
            if 'image' in changes:
                if changes['image'] is None:
                    return

                height, width, channels = changes['image'].shape

                # compensate display size
                scale = 1
                if self.state['downsample'] == 'half':
                    scale = 2
                elif self.state['downsample'] == 'quarter':
                    scale = 4

                resolution_label.setText("{}x{}".format(width*scale, height*scale))

        statusbar.addPermanentWidget(resolution_label)

        # add fps label to statusbar
        statusbar.addPermanentWidget(fps_label)

        # add oscilloscope to statusbar
        statusbar.addPermanentWidget(oscilloscope)

        @self.state_changed.connect
        def update_timer_interval(changes):
            if 'fps' in changes:
                # update fps label
                interval = int(1000/changes['fps']) if changes['fps'] else 0
                statusbar.showMessage(f"{1000/interval if interval>0 else 'inf'}")

        return statusbar

    def init_gui(self)->None:
        # View
        # ----
        self.setLayout(QVBoxLayout())
        self.layout().setContentsMargins(0,0,0,0)
        self.layout().setSpacing(0)

        # Create custom window frame
        # self.setWindowFlags(Qt.FramelessWindowHint)

        # window title
        @self.state_changed.connect
        def update_title(changes):
            if 'path' in changes:
                title = "VideoPlayer"
                if self.state['path']:
                    title = "{} {}".format(title, self.state['path'] or "")
                self.setWindowTitle(title)

        menubar = self.create_menubar()
        self.layout().addWidget(menubar)

        image_toolbar = self.create_image_toolbar()
        self.layout().addWidget(image_toolbar)

        image_viewer = self.create_image_viewer()
        self.layout().addWidget(image_viewer)

        time_controls = self.create_time_controls()
        self.layout().addWidget(time_controls)

        statusbar = self.create_statusbar()
        self.layout().addWidget(statusbar)

        # Create Playback Timer
        # =====================
        playback_timer = QTimer()
        playback_timer.setTimerType(Qt.PreciseTimer)

        @self.state_changed.connect
        def update_timer_playback(changes):
            if 'playback' in changes:
                if changes['playback'] == "forward" or changes['playback'] == "reverse":
                    interval = int(1000/self.state['fps']) if self.state['fps'] else 0
                    playback_timer.start(interval)
                if changes['playback'] == "paused":
                    playback_timer.stop()

        @self.state_changed.connect
        def update_timer_interval(changes):
            if 'fps' in changes:
                interval = int(1000/changes['fps']) if changes['fps'] else 0

                # Update timer interval based on fps
                if playback_timer.interval() != interval:
                    playback_timer.setInterval(interval)

        def next_frame():
            left = max(self.state['inpoint'], self.state['range'][0])
            right = min(self.state['outpoint'], self.state['range'][1])

            if self.state['playback'] == "forward":
                frame = self.state['frame']+1
                if frame>right:
                    frame = left

                self.set_state(frame=frame)

            elif self.state["playback"] == "reverse":
                frame = self.state['frame']-1
                if frame<left:
                    frame = right

                self.set_state(frame=frame)

            else:
                raise Exception("timer not supposed to tick while paused")

        playback_timer.timeout.connect(next_frame)

        @self.state_changed.connect
        def pause_timer_until_frame_loaded(changes):
            # Pause timer until frame is loaded
            IsPlaying = self.state['playback'] in {"forward", "reverse"}
            IsFrameAvailable = self.make_key() not in self.frame_server

            if 'frame' in changes or 'image' in changes:
                if IsPlaying:
                    if playback_timer.isActive() and IsFrameAvailable:
                        # puase timer until frame is loaded
                        playback_timer.stop()
                    else:
                        # resume timer when frame loaded
                        playback_timer.start()

        


        # Create export dialog
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

        # Handle drar and drop
        self.setAcceptDrops(True)
        image_viewer.setAcceptDrops(False)

    # EVENTS

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

    def resizeEvent(self, event):
        # uodate viewer
        if self.state['zoom'] == "fit":
            self.fit()

    def closeEvent(self, event):
        self.running = False
        print("close")

    # COMMANDS

    def open(self, filename=None):
        if not filename:
            filename, filters = QFileDialog.getOpenFileName(self, "Open Image", "/")

        if not filename:
            return
        
        # update video capture
        self.set_state(path=filename)

        # # update viewer
        # image_viewer.fitInView(image_scene.sceneRect(), Qt.KeepAspectRatio)

    def open_lut(self, filename=None):
        if not filename:
            filename, filters = QFileDialog.getOpenFileName()

        if not filename:
            return

        self.set_state(lut_path=filename, lut_enabled=True)

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
            ext = str(Path(filename).suffix)
            path = str(Path(Path(filename).parent, Path(filename).stem))
            assert ext in {'.mp4', '.jpg'}

            first_frame, last_frame = self.state['range']
            duration = last_frame-first_frame
            fps = self.state['fps']
            lut = self.state['lut_path'] if self.state['lut_enabled'] else None
            process_desc = ProcessDesc(path=self.state['path'], frame=first_frame, downsample="full", lut=lut)
            height, width, channels = self.evaluate(process_desc).shape

            IsSequence = ext == ".jpg"
            IsMovie = ext == ".mp4"

            if IsSequence:
                for frame in range(first_frame, last_frame+1):
                    progress = int(100*(frame-first_frame)/(last_frame-first_frame))

                    process_desc = ProcessDesc(path=self.state['path'], frame=frame, downsample="full", lut=lut)
                    rgb = self.evaluate(process_desc).copy()
                    assert rgb.shape == (height, width, channels)
                    # bgr = rgb[...,::-1].copy()
                    
                    frame_filename = path+("%05d" % frame)+ext
                    print("create output", frame_filename)
                    out = oiio.ImageOutput.create(frame_filename)
                    if not out:
                        print(ext, "format is not supported")
                        return
                    spec = oiio.ImageSpec(width, height, channels, oiio.TypeUInt8)

                    print("wrtie image")
                    out.open(frame_filename, spec)
                    out.write_image(rgb)
                    out.close()

                    # update state
                    self.set_state(export= {
                        'visible': self.state['export']['visible'],
                        'filename': filename,
                        'progress': frame
                    })

            if IsMovie:
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                writer = cv2.VideoWriter(filename,fourcc, fps or 24, (width, height))
                for frame in range(first_frame, last_frame+1):
                    progress = int(100*(frame-first_frame)/(last_frame-first_frame))
                    process_desc = ProcessDesc(path=self.state['path'], frame=frame, downsample="full", lut=lut)
                    rgb = self.evaluate(process_desc).copy()
                    bgr = rgb[...,::-1].copy()

                    writer.write(bgr)

                    # update state
                    self.set_state(export= {
                        'visible': self.state['export']['visible'],
                        'filename': filename,
                        'progress': frame
                    })
                writer.release()

        the_thread = threading.Thread(target=run, daemon=True).start()

    def toggleFullscreen(self):
        raise NotImplementedError
        # if self.dialog.isVisible():
        #     self.layout().addWidget(image_viewer)
        #     self.dialog.hide()
        # else:
        #     self.dialog.show()
        #     self.dialog.setWindowState(Qt.WindowFullScreen)
        #     self.dialog.layout().addWidget(image_viewer)

    def fit(self):
        # image in viewer
        self.set_state(zoom="fit")


def main():
    import sys
    from widgets.themes import apply_dark_theme2

    """ Setup Application with theme"""
    app = QApplication.instance() or QApplication()
    apply_dark_theme2(app)
    # from experiments.qss_hotreload import QSSHotreload
    # QSSHotreload("./style.qss")
    
    """Setup VideoPlayer"""
    window = VideoPlayer()
    window.show()
    window.open_lut("../tests/resources/AlexaV3_K1S1_LogC2Video_Rec709_EE_aftereffects3d.cube")
    window.open("../tests/resources/MASA_sequence/MASA_sequence_00196.jpg")
    # window.open("../tests/resources/EF_VFX_04/EF_VFX_04_0094900.dpx")
    window.set_state(fps=0, memory_limit=1000)

    """Launch app"""
    app.exec()


def time_apply_lut():
    import OpenImageIO as oiio
    image = oiio.ImageBuf("../tests/resources/MASA_sequence/MASA_sequence_00196.jpg")
    pixels = image.get_pixels()
    lut = read_lut("../tests/resources/AlexaV3_K1S1_LogC2Video_Rec709_EE_aftereffects3d.cube")
    begin = time.time()

    print("apply lut", apply_lut)
    apply_lut(pixels, lut)
    print( 1/(time.time()-begin))

    begin = time.time()
    apply_lut(pixels, lut)
    print( "apply lut time: ", time.time()-begin)


if __name__ == "__main__":
    time_apply_lut()
    main()