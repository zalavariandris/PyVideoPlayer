import numpy as np
cimport numpy as np
from cython cimport boundscheck, wraparound, nonecheck, cdivision
from libc.math cimport floor, ceil, round

DTYPE = np.float32
ctypedef np.float32_t DTYPE_t

@boundscheck(False)
@wraparound(False)
@nonecheck(False)
@cdivision(True)
def apply_lut_cython(np.ndarray[DTYPE_t, ndim=3] pixels, np.ndarray[DTYPE_t, ndim=4] lut):
    cdef int h = pixels.shape[0]
    cdef int w = pixels.shape[1]
    cdef int c = pixels.shape[2]
    cdef int i, x, y, ri, gi, bi, count
    cdef int lut_width = lut.shape[0]
    cdef int lut_height = lut.shape[1]
    cdef int lut_depth = lut.shape[2]
    cdef DTYPE_t r,g,b
    cdef np.ndarray[DTYPE_t, ndim=3] dst

    dst = np.zeros( (h,w,c), dtype=DTYPE )
    count = pixels.shape[1]*pixels.shape[0]
    for i in range( count ):
        x = i%w
        y = i//w

        # get src color
        r = pixels[y,x,0]
        g = pixels[y,x,1]
        b = pixels[y,x,2]

        # lookup color
        r0 = <int>floor(r*(lut_width-1))
        r1 = <int>r0+1
        g0 = <int>floor(g*(lut_height-1))
        g1 = g0+1
        b0 = <int>floor(b*(lut_depth-1))
        b1 = b0+1

        dst[y,x,0] = <float>lut[b0, g0, r0, 0]
        dst[y,x,1] = <float>lut[b0, g0, r0, 1]
        dst[y,x,2] = <float>lut[b0, g0, r0, 2]

    return dst