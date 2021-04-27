import colour
import numpy as np
import matplotlib.pyplot as plt

def read_lut(path):
    lut = colour.read_LUT(path)
    return lut
    
def apply_lut(src, lut):
    dst = lut.apply(src)
    return dst

if __name__ == "__main__":
    from pathlib import Path
    import cv2
    path = Path('../tests/resources/ACES_Proxy_10_to_ACES.cube').resolve()
    lut = read_lut(path)

    bgr = cv2.imread("../tests/MASA_sequence/MASA_sequence_00196.jpg")
    rgb = bgr[:, :, ::-1].astype(np.float32)/255
    rgb = apply_lut(rgb, lut)

    plt.imshow(rgb)
    plt.show()