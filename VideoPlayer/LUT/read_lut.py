from pathlib import Path
import numpy as np

def read_lut(path):
	assert Path(path).exists()

	data = []
	size = -1
	for line in Path(path).read_text().split("\n"):
	    if line.strip() == "":
	        continue
	    elif line[0] == "#":
	        continue
	    elif line.split()[0] == "LUT_1D_SIZE":
	        size = int( line.split()[1] )
	        kind = "1D"
	    elif line.split()[0] == "LUT_3D_SIZE":
	        size = int( line.split()[1] )
	        kind = "3D"
	    else:
	        data.append( [float(part) for part in line.split()] )

	return np.array(data).reshape(size, size, size, 3).astype(np.float32)

if __name__ == "__main__":
	lut = read_lut("../../tests/resources/AlexaV3_K1S1_LogC2Video_Rec709_EE_aftereffects3d.cube")
	print(lut.shape)