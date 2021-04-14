import unittest
import sys
import numpy as np
sys.path.append('../')

from VideoPlayer.reader import Reader, parse_sequence

class TestReader(unittest.TestCase):
	def test_read_from_mp4(self):
		reader = Reader("Mása - becsukjuk, nem latszik.mp4")
		img = reader.read(0)

		self.assertEqual(img.dtype, np.uint8)
		self.assertEqual(img.shape[2], 3) # RGB

	def test_read_from_sequence(self):
		reader = Reader("MASA_sequence/MASA_sequence_00196.jpg")

		img = reader.read(196)

		self.assertEqual(img.dtype, np.uint8)
		self.assertEqual(img.shape[2], 3) # RGB

	def test_metadata_from_mp4(self):
		reader = Reader("Mása - becsukjuk, nem latszik.mp4")
		self.assertEqual(reader.fps, 25.0)
		self.assertEqual(reader.first_frame, 0)
		self.assertGreater(reader.last_frame, 0)

	def test_metadata_from_sequence(self):
		reader = Reader("MASA_sequence/MASA_sequence_00196.jpg")

		self.assertEqual(reader.fps, None)
		self.assertEqual(reader.first_frame, 196)
		self.assertEqual(reader.last_frame, 300)

		
	def test_metadata_from_large_DPX_sequence(self):
		path = "R:/Frank/Final/EF_VFX_04_v62/EF_VFX_04_MERGE_v62_93230.dpx"
		seq = parse_sequence(path)
		reader = Reader(path)

		self.assertEqual(reader.fps, None)
		self.assertEqual(reader.first_frame, 93230)
		self.assertEqual(reader.last_frame, 94901)

		img = reader.read(93230)
		self.assertEqual(img.dtype, np.uint8)
		self.assertEqual(img.shape[2], 3) # RGB


if __name__ == '__main__':
    unittest.main()