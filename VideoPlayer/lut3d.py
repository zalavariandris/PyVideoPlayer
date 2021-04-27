# ref from here https://gist.github.com/arsenyinfo/74e42b41749cf29a7bbb69ed839bff1a

from functools import partial

import numpy as np
from tqdm import tqdm

LUT_SIZE = 32

def _convert(pixel, lut):
    r, g, b = map(lambda x: round((x / 255) * LUT_SIZE - 1), pixel)
    idx = r + g * LUT_SIZE + b * (LUT_SIZE ** 2)
    result = lut[int(idx)]
    r_, g_, b_ = map(lambda i: float(result[i]), range(3))
    return np.array([r_, g_, b_])

def read_lut(path):
    with open(path) as fd:
        lines = [x.rstrip() for x in fd.readlines()]
    lut = list(map(lambda x: x.split(' '), lines[-LUT_SIZE**3: ]))
    return lut

def apply_lut(img, lut):
    # print(lut)
    pixels = img.reshape(-1, 3)
    convert = partial(_convert, lut=lut)
    new_pixels = list(map(convert, tqdm(pixels)))
    new_img = np.array(new_pixels).reshape(img.shape)
    
    new_img = (new_img * 255).astype('uint8')
    
    return new_img

if __name__ == "__main__":
    import matplotlib.pyplot as plt
    from pathlib import Path
    import cv2
    lut_path = Path('../tests/resources/AlexaV3_K1S1_LogC2Video_Rec709_EE_aftereffects3d.cube').resolve()
    

    bgr = cv2.imread("../tests/resources/MASA_sequence/MASA_sequence_00196.jpg")
    rgb = bgr[:, :, ::-1]
    # rgb = rgb.astype(np.float32)/255

    rgb = apply_lut(rgb, read_lut(lut_path))

    # rgb = apply_lut(rgb, lut)



    plt.imshow(rgb)
    plt.show()