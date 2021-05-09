from read_lut import read_lut
from apply_lut_cython import apply_lut_cython as apply_lut
import OpenImageIO as OIIO
from pathlib import Path
import numpy as np
import time

if __name__ == "__main__":
	# read image
	path = "../../tests/resources/MASA_sequence/MASA_sequence_00196.jpg"
	path = "../../tests/resources/EF_VFX_04/EF_VFX_04_0094901.dpx"
	assert Path(path).exists()
	image = OIIO.ImageBuf(path)
	pixels = image.get_pixels()

	#read lut
	lut = read_lut("../../tests/resources/AlexaV3_K1S1_LogC2Video_Rec709_EE_aftereffects3d.cube")

	# apply lut
	t = time.time()
	dst = apply_lut(pixels, lut)
	print("{:.3f}s".format(time.time()-t))

	# show image
	import matplotlib.pyplot as plt
	plt.imshow(dst)
	plt.show()
