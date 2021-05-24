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

# from distutils.core import setup
# from Cython.Build import cythonize
# from distutils.extension import Extension
# from Cython.Distutils import build_ext

# ext_modules=[
#     Extension("VideoPlayer",
#               ["./VideoPlayer/LUT/apply_lut_cython.pyx"],
#               # libraries=["m"],
#               extra_compile_args = ["-O2", "-ffast-math", "-march=native", "-fopenmp" ],
#               extra_link_args=['-fopenmp']
#               ) 
# ]

# setup( 
# 	name = "VideoPlayer",
# 	cmdclass = {"build_ext": build_ext},
# 	ext_modules = ext_modules,
# 	include_dirs=[numpy.get_include()],
# 	# zip_safe=False,
# 	# language_level=3
# )