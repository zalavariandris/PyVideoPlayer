# PyVideoPlayer

This is a simple work in progress image sequence player built with python3 pyside6 and opencv.

## TODO
- [x] create exe
- [x] open files directly by *open with* or *drag and drop*
- [x] implement Viewer
- [x] add zoom and zoom to fit fit
- [x] zoom around mouse cursor
- [x] zoom around pinch center
- [x] reimplement pan, interferes with zoomt around pinch center

- [x] fix is_sequence when video files eg .mp4 ends with a number
- [x] Reader class to support sequence starts at non zero
- [x] loop by default
- [ ] add loop option in gui
- [ ] fix timer. QTimer works with int milliseconds. Eg. 24 fps is 1000/fps=41.66 will set the timer to 41ms frequency.
- [x] export to mp4
- [x] add non blobking export with gui
- [x] dark theme
- [x] fix first frame number when image sequence starts other than 0
- [ ] fullscreen
- [ ] fullscreen scrubbing
- [ ] support 16 and 32bit image formats
- [ ] drag and drop
- [ ] create a precise framespinner widget with matching cache bar
- [ ] mark in, out point
- [ ] expusure, gamma
- [ ] LUT
- [ ] give it a better name : )

## Build with PyInstaller
> pyinstaller VideoPlayer/main.py

## How to build with nuitka
> python -m nuitka --mingw64 VideoPlayer/main.py

or standalone:

> python -m nuitka --mingw64 --standalone --plugin-enable=numpy --plugin-enable=pyside6 VideoPlayer/main.py
