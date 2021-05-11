from LUT import read_lut, apply_lut
from read import Reader
import cv2
import numpy as np
from functools import cache

from enum import Enum

@cache
def create_reader(path):
	return Reader(path)

def read_image(image_path, frame):
	reader = create_reader(image_path)
	image = reader.read(frame)
	return image.astype(np.float32)/255

def resize_image(image, width:int, height:int):
    image = cv2.resize(image, 
        dsize=(width, height), 
        interpolation=cv2.INTER_NEAREST)
    return image

def evaluate(frame, path, downsample=None, lut=None):
	image = read_image(path, frame)
	if downsample is not None:
		height, width, channels = image.shape
		factor = [1,2,4][ ['full', 'half', 'quarter'].index(downsample) ]
		image = resize_image(image, int(width/factor), int(height/factor))
	if lut is not None:
		image = apply_lut(image, cache(read_lut)(lut))
	return image

def main():
	import matplotlib.pyplot as plt
	import time
	from pathlib import Path
	image_path = "../tests/resources/MASA_sequence/MASA_sequence_00196.jpg"
	assert Path(image_path).exists()
	downsample = 'half'
	lut_path = "../tests/resources/AlexaV3_K1S1_LogC2Video_Rec709_EE_aftereffects3d.cube"
	assert Path(lut_path).exists()

	ys = []
	for frame in range(195, 255):
		begin = time.time()
		image = evaluate(frame, image_path, downsample, lut_path)
		dt = time.time() - begin
		ys.append(dt)

	plt.plot(ys)

	print(ys)
	# plt.imshow(image)
	plt.show()

if __name__ == "__main__":
	main()
