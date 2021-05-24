from PySide6.QtCore import *
from dataclasses import dataclass
from functools import cache
import numpy as np
import threading
import time
from read import Reader
from LUT import read_lut, apply_lut
import cv2

from pathlib import Path

from typing import Iterable

@dataclass(frozen=True)
class ProcessDesc:
    path: str
    frame: int
    downsample: str
    lut: str

    def is_valid(self):
        return (isinstance(self.path, str) and Path(self.path).exists() and 
            isinstance(self.frame, int) and 
            isinstance(self.downsample, str))


@cache
def read_lut_cached(lut_path):
    print("read lut", lut_path)
    return read_lut(lut_path)

@cache 
def create_reader_cached(path):
    return Reader(path)



class FrameServer(QObject):
    cache_changed = Signal()
    frame_done = Signal(ProcessDesc)

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self._lut = None
        self._reader = None

        self.times = dict() # profile

        self.memory_limit = 100 #MB

        self._cache = dict()
        self._requested_frames = []

        self.worker = threading.Thread(target=self.preload, daemon=True)
        self.running = True
        self.lock = threading.Lock()
        self.worker.start()

        self.scrub_event = threading.Event()

        self.hints = None # playing forward || playing backward || scrubbing | paused

        # self._current_frame = None
        # self._current_image = None

    def evaluate(self, key:ProcessDesc, rect=None)->np.ndarray:
        if key.path is None:
            return None
            # raise Exception("invalid process description")

        if key.path is not None:
            self._reader = create_reader_cached(key.path)

        if key.lut is not None:
            self._lut = read_lut_cached(key.lut).astype(np.float32)

        with self.lock:
            # read
            begin = time.time()
            data = self._reader.read(key.frame).astype(np.float32)/255
            self.times['read'] = time.time()-begin

            # resize
            begin = time.time()
            idx = ['full', 'half', 'quarter'].index(key.downsample)
            factor = [1,2,4][idx]

            data = cv2.resize(data, 
                dsize=(data.shape[1]//factor, data.shape[0]//factor), 
                interpolation=cv2.INTER_NEAREST)
            self.times['resize'] = time.time()-begin

            # apply lut
            begin = time.time()
            if self._lut is not None and key.lut is not None:
                data = apply_lut(data, self._lut)
            self.times['lut'] = time.time()-begin

        return (data*255).astype(np.uint8)

    def used_memory(self):
        megabytes = 0
        for key, (pixels, timestamp) in self._cache.items():
            megabytes+=pixels.nbytes / 1024 / 1024 # in MB
        return megabytes

    def preload(self)->None:
        while self.running:
            time.sleep(0.00000001)

            while self.used_memory() > self.memory_limit and self.running:
                # find oldest cache item
                oldest_key = None
                current_timestamp = time.time()
                for key, (pixels, timestamp) in self._cache.items():
                    if  timestamp<current_timestamp:
                        current_timestamp = timestamp
                        oldest_key = key

                # delete last cache item
                assert oldest_key is not None
                del self._cache[oldest_key]
                print("del", oldest_key.frame)
                self.cache_changed.emit()

                # if oldest_key == self._current_frame:
                #     self.image_changed.emit()

            if self._requested_frames and self.running:
                key = self._requested_frames.pop()


                # print("preload frame", frame, threading.current_thread())
                
                img = self.evaluate(key)

                if img is not None:
                    with self.lock:
                        # print("read frame: ", frame)
                        downsample = key.downsample
                        lut = key.lut
                        self._cache[key] = (img, time.time())
                        self.cache_changed.emit()
                        # print("emit frame done", "frame is loaded")
                        self.frame_done.emit(key)

                        # if key == self._current_frame:
                        #     self.image_changed.emit()
                        # self.cache_updated.emit()
                        # self.set_state(cache=self.state['cache'])

    def request_frame(self, key:ProcessDesc)->None:
        if key in self._cache:
            # self._current_frame = key
            # self.image_changed.emit()
            # print("emit frame done", "frame is cached")
            self.frame_done.emit(key)
        else:
            # self._current_frame = key
            # print("request processing frame")
            self._requested_frames = [key]

    def __getitem__(self, key:ProcessDesc)->np.ndarray:
        pixels, timestamp = self._cache[key]
        return pixels

    def __contains__(self, key:ProcessDesc)->bool:
        return key in self._cache

    def __iter__(self)->Iterable[ProcessDesc]:
        for key in self._cache:
            yield key

    def clear_cache(self):
        self._cache = {}