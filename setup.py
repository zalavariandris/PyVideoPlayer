from setuptools import setup
from Cython.Build import cythonize
import numpy

setup(
    name='VideoPlayer',
    ext_modules=cythonize("VideoPlayer/LUT/apply_lut_cython.pyx"),
    include_dirs=[numpy.get_include()],
    zip_safe=False,
    language_level=3
)