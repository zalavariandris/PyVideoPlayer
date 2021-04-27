# used as reference: https://github.com/thibauts/apply-cube-lut

from dataclasses import dataclass

@dataclass
class LUT:
    title: str
    domain: tuple
    kind: str
    size: int
    data: list


def read_lut(path):
    with open(path) as fd:
        lines = [x.rstrip() for x in fd.readlines()]
    # lut = list(map(lambda x: x.split(' '), lines[-LUT_SIZE**3: ]))


    title = None;
    domain = [(0.0, 0.0, 0.0), (1.0, 1.0, 1.0)]
    kind = None
    data = []
    size = None
#   var type = null;
#   var size = 0;
#   var domain = [[0.0, 0.0, 0.0], [1.0, 1.0, 1.0]];
#   var data = [];

#   var lines = str.split('\n');
    print("lines", lines)
    print("parse:")
    for line in lines:
        if line == '' or line[0] == '#':
            continue
#       // Skip comments and empty lines
#       continue;
#     }

        parts = line.split()
        print(parts)
        if parts[0] == 'TITLE':
            title = line[7:-1]
        elif parts[0] == 'DOMAIN_MIN':
            domain[0] = parts[1:]
        elif parts[0] == 'DOMAIN_MAX':
            domain[1] = parts[1:]
        elif parts[0] == 'LUT_1D_SIZE':
            kind = '1D'
            size = int(parts[1])
        elif parts[0] == 'LUT_3D_SIZE':
            kind = '3D'
            size = int(parts[1])
        else:
            data.append([float(part) for part in parts])


    return LUT(title, domain, kind, size, data)

import numpy as np
def apply_lut(img, lut):
    if lut.kind == '1D':
        shape = [lut.size, 3]
    elif lut.kind == '3D':
        shape = [lut.size, lut.size, lut.size, 3]
    else:
        raise NotImplementedError

    flat = np.array(lut.data).reshape(-1)
    grid = flat.reshape(shape)
    dmin = lut.domain[0]
    dmax = lut.domain[1]

    dest = np.zeros( img.shape )

    # for y in range(img.shape[0]):
    #     for x in range(img.shape[1]):
    #         ri = img[x,y,0]
    #         gi = img[x,y,1]
    #         bi = img[x,y,2]

    #         # map to domain
    #         ri = (ri - dmin[0]) / (dmax[0] - dmin[0])
    #         gi = (gi - dmin[1]) / (dmax[1] - dmin[1])
    #         bi = (bi - dmin[2]) / (dmax[2] - dmin[2])

    #         # map to grid units
    #         ri = ri * (lut.size - 1)
    #         gi = gi * (lut.size - 1)
    #         bi = bi * (lut.size - 1)

    #         ri = 0 if ri < 0 else (lut.size - 1 if ri > (lut.size - 1) else ri)
    #         gi = 0 if gi < 0 else (lut.size - 1 if gi > (lut.size - 1) else gi)
    #         bi = 0 if bi < 0 else (lut.size - 1 if bi > (lut.size - 1) else bi)

    #         if lut.kind == '1D':
    #             ro = np.interp(grid, [ri], [0])
    #             go = np.interp(grid, [gi], [1])
    #             bo = np.interp(grid, [bi], [2])
    #         else:
    #             # lut.type === '3D'
    #             # Note `bi` is the fastest changing component
    #             ro = lerp(grid, bi, gi, ri, 0)
    #             go = lerp(grid, bi, gi, ri, 1)
    #             bo = lerp(grid, bi, gi, ri, 2)

    #         dest[x, y, 0] = ro
    #         dest[x, y, 1] = go
    #         dest[x, y, 2] = bo

      # var flat = flatten(lut.data);

      # var grid = ndarray(flat, shape);
      # var dmin = lut.domain[0];
      # var dmax = lut.domain[1];

      # for(y=0; y<src.shape[1]; y++) {
      #   for(x=0; x<src.shape[0]; x++) {
      #     var ri = src.get(x, y, 0);
      #     var gi = src.get(x, y, 1);
      #     var bi = src.get(x, y, 2);

      #     // map to domain
      #     ri = (ri - dmin[0]) / (dmax[0] - dmin[0]);
      #     gi = (gi - dmin[1]) / (dmax[1] - dmin[1]);
      #     bi = (bi - dmin[2]) / (dmax[2] - dmin[2]);

      #     // map to grid units
      #     ri = ri * (lut.size - 1);
      #     gi = gi * (lut.size - 1);
      #     bi = bi * (lut.size - 1);

      #     // clamp to grid bounds
      #     ri = ri < 0 ? 0 : (ri > (lut.size - 1) ? (lut.size - 1) : ri);
      #     gi = gi < 0 ? 0 : (gi > (lut.size - 1) ? (lut.size - 1) : gi);
      #     bi = bi < 0 ? 0 : (bi > (lut.size - 1) ? (lut.size - 1) : bi);

      #     if(lut.type === '1D') {
      #       var ro = lerp(grid, ri, 0);
      #       var go = lerp(grid, gi, 1);
      #       var bo = lerp(grid, bi, 2);
      #     } else {
      #       // lut.type === '3D'
      #       // Note `bi` is the fastest changing component
      #       var ro = lerp(grid, bi, gi, ri, 0);
      #       var go = lerp(grid, bi, gi, ri, 1);
      #       var bo = lerp(grid, bi, gi, ri, 2);
      #     }

      #     dest.set(x, y, 0, ro);
      #     dest.set(x, y, 1, go);
      #     dest.set(x, y, 2, bo);
      #   }
      # }

    return dest

if __name__ == "__main__":
    import matplotlib.pyplot as plt
    from pathlib import Path
    import cv2
    lut_path = Path('../tests/resources/ACES_Proxy_10_to_ACES.cube').resolve()
    lut = read_lut(lut_path)
    

    print(lut)

    bgr = cv2.imread("../tests/resources/MASA_sequence/MASA_sequence_00196.jpg")
    rgb = bgr[:, :, ::-1]

    rgb = apply_lut(rgb, lut)

    # bgr = cv2.imread("../tests/resources/MASA_sequence/MASA_sequence_00196.jpg")
    # rgb = bgr[:, :, ::-1]
    # # rgb = rgb.astype(np.float32)/255

    # rgb = apply_lut(rgb, lut)

    # # rgb = apply_lut(rgb, lut)



    plt.imshow(rgb)
    plt.show()