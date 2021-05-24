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
def apply_lut_cython(DTYPE_t[:,:,::1] pixels, DTYPE_t[:,:,:,::1] lut):
    # pixels variables
    cdef int height = pixels.shape[0]
    cdef int width = pixels.shape[1]
    cdef int channels = pixels.shape[2]
    cdef int i, u, v, count

    # lut variables
    cdef int X = lut.shape[0]
    cdef int Y = lut.shape[1]
    cdef int Z = lut.shape[2]
    
    # result
    cdef np.ndarray[DTYPE_t, ndim=3] dst

    # interpolation definitions
    cdef DTYPE_t x,y,z
    cdef int x0, y0, z0, x1, y1, z1
    cdef DTYPE_t xd, yd, zd, c00, c01, c10, c11, c0, c1, c_blue, c_green, c_red

    dst = np.empty( (height, width, channels), dtype=DTYPE )
    cdef DTYPE_t[:,:,::1] result_view = dst

    for i in range(width * height):
        u = i%width
        v = i//width

        # get src color
        x = pixels[v,u,0] * X
        y = pixels[v,u,1] * Y
        z = pixels[v,u,2] * Z

        # lookup cube coordinates
        x0 = <int>floor( x )
        x1 = x0+1
        y0 = <int>floor( y )
        y1 = y0+1
        z0 = <int>floor( z )
        z1 = z0+1

        xd = (x-x0)/(x1-x0)
        yd = (y-y0)/(y1-y0)
        zd = (z-z0)/(z1-z0)
        
        # Trilinear Interpolation
        #  blue
        c00 = lut[z0, y0, x0, 0]*(1-xd) + lut[z0, y0, x1, 0]*xd
        c01 = lut[z1, y0, x0, 0]*(1-xd) + lut[z1, y0, x1, 0]*xd
        c10 = lut[z0, y1, x0, 0]*(1-xd) + lut[z0, y1, x1, 0]*xd
        c11 = lut[z1, y1, x0, 0]*(1-xd) + lut[z1, y1, x1, 0]*xd

        c0 = c00*(1-yd) + c10*yd
        c1 = c01*(1-yd) + c11*yd

        c_blue = c0*(1-zd) + c1*zd

        #  green
        c00 = lut[z0, y0, x0, 1]*(1-xd) + lut[z0, y0, x1, 1]*xd
        c01 = lut[z1, y0, x0, 1]*(1-xd) + lut[z1, y0, x1, 1]*xd
        c10 = lut[z0, y1, x0, 1]*(1-xd) + lut[z0, y1, x1, 1]*xd
        c11 = lut[z1, y1, x0, 1]*(1-xd) + lut[z1, y1, x1, 1]*xd

        c0 = c00*(1-yd) + c10*yd
        c1 = c01*(1-yd) + c11*yd

        c_green = c0*(1-zd) + c1*zd

        #  red
        c00 = lut[z0, y0, x0, 2]*(1-xd) + lut[z0, y0, x1, 2]*xd
        c01 = lut[z1, y0, x0, 2]*(1-xd) + lut[z1, y0, x1, 2]*xd
        c10 = lut[z0, y1, x0, 2]*(1-xd) + lut[z0, y1, x1, 2]*xd
        c11 = lut[z1, y1, x0, 2]*(1-xd) + lut[z1, y1, x1, 2]*xd

        c0 = c00*(1-yd) + c10*yd
        c1 = c01*(1-yd) + c11*yd

        c_red = c0*(1-zd) + c1*zd

        # set destination color
        result_view[v,u,0] = c_blue
        result_view[v,u,1] = c_green
        result_view[v,u,2] = c_red

    return dst

    