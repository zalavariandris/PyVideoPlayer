import unittest
import sys
import numpy as np
sys.path.append('../')

from VideoPlayer.reader import Reader

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
		print(reader.fps)
		self.assertEqual(reader.fps, 25.0)
		self.assertEqual(reader.first_frame, 0)
		self.assertGreater(reader.last_frame, 0)

	def test_metadata_from_sequence(self):
		reader = Reader("MASA_sequence/MASA_sequence_00196.jpg")

		self.assertEqual(reader.fps, None)
		self.assertEqual(reader.first_frame, 196)
		self.assertEqual(reader.last_frame, 300)


if __name__ == '__main__':
    unittest.main()