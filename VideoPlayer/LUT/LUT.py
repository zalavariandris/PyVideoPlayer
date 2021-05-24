
from . import read_lut, apply_lut
import numpy as np

class LUT:
	def __init__(self, path):
		self.data:np.ndarray = read_lut(path)

	def apply(self, pixels:np.ndarray)->np.ndarray:
		return apply_lut(pixels)
