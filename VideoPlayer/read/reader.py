import glob
import re
from pathlib import Path
import cv2
import numpy as np
from typing  import *

import mimetypes
import os
import string

import OpenImageIO as oiio

""" sequence
getFileNameList: return a list of filesin a folder.
concatenating sequences like so:
|     name         |   range   |
|image.jpg
|sequence.####.exr | 1001-1100 |

"""

def is_sequence(filePath:str)->bool:
    path, ext = os.path.splitext(filePath)
    mime, encoding = mimetypes.guess_type(filePath)
    if not mime:
        if ext == ".dpx":
            mime = "image/x-dpg"
    # print("is sequence:", mime, encoding)
    if mime.split('/')[0] == "video":
        return False
    
    return path.rstrip(string.digits) != path

def parse_sequence(path: str)->Tuple[str,int,int]:
    """
    return:
      first_frame: the first frame of the sequence
      last_Frame: the last frame of the sequence
      sequence_path in format: {folder}/{filename}d{5}.{ext}
      return (sequence_path, first_frame, last_frame)
    """
    folder, name = os.path.split(path)
    base, ext = os.path.splitext(name)
    folder = os.path.dirname(path)
    base_no_digits = base.rstrip(string.digits)
    digits_length = len(base)-len(base_no_digits)
    digits_match = "d{"+str(digits_length)+"}"

    name_pattern = f"{base_no_digits}\{digits_match}\{ext}$"

    files = sorted( [f for f in os.listdir(folder) if re.match(name_pattern, f)] )
    first_file = os.path.splitext(files[0])[0]
    last_file = os.path.splitext(files[-1])[0]
    first_frame = int(first_file[-digits_length:])
    last_frame = int(last_file[-digits_length:])

    # compose sequence path eg: folder/filename_%5d.jpg
    sequence_path = f"{folder}/{base_no_digits}%0{digits_length}d{ext}"

    # return sequence metadata
    return sequence_path, first_frame, last_frame


from pathlib import Path
class Reader:
    def __init__(self, path):
        self._is_sequence = is_sequence(path)
        self._path = path
        assert Path(path).exists()
        if self._is_sequence:
            # IMAGE SEQUENCE
            self._cap = None
            self._image = oiio.ImageInput.open(path)
            self._is_sequence = True

            # get metadata
            sequence_path, first_frame, last_frame = parse_sequence(self._path)
            self._sequence_path = sequence_path
            self._first_frame = first_frame
            self._last_frame = last_frame
            self._fps = None
            self._width = self._image.spec().width
            self._height = self._image.spec().height
        
        else:
            # VIDEO FILE
            self._is_sequence = False
            self._cap = cv2.VideoCapture(path)
            self._image = None

            # get metadata
            self._first_frame = 0
            self._last_frame = int(self._cap.get(cv2.CAP_PROP_FRAME_COUNT))-1
            self._fps = self._cap.get(cv2.CAP_PROP_FPS)
            self._width = int( self._cap.get(cv2.CAP_PROP_FRAME_WIDTH) )
            self._height = int( self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT) )
            
    def read(self, frame: int)->np.ndarray:
        if frame < self._first_frame:
            frame = self._first_frame

        if frame > self._last_frame:
            frame = self._last_frame

        if self._is_sequence:
            frame_path = self._sequence_path % frame
            name, ext = os.path.splitext(frame_path)

            inputImage = oiio.ImageBuf( frame_path )
            rgb = (inputImage.get_pixels()*255).astype(np.uint8)
            # inputImage.close()

            # 
            rgb.flags.writeable = False
            return rgb
        else:
            if self._cap.get(cv2.CAP_PROP_POS_FRAMES)!=frame:
                self._cap.set(cv2.CAP_PROP_POS_FRAMES, frame)
            ret, bgr = self._cap.read()
            
            if ret:
                rgb = bgr[...,::-1].copy()
                rgb.flags.writeable = False
                return rgb
            else:
                return None

    @property
    def width(self)->int:
        return self._width

    @property
    def height(self):
        return self._height

    @property
    def first_frame(self)->int:
        return self._first_frame

    @property
    def last_frame(self)->int:
        return self._last_frame

    @property
    def fps(self)->float:
        return self._fps

    def __hash__(self):
        return hash(self.path)
