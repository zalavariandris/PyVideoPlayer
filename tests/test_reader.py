import unittest
import sys
import numpy as np
sys.path.append('../')

from VideoPlayer.reader import Reader, parse_sequence

class TestReader(unittest.TestCase):
	def test_read_from_mp4(self):
		reader = Reader("./resources/Mása - becsukjuk, nem latszik.mp4")
		img = reader.read(0)

		self.assertEqual(img.dtype, np.uint8)
		self.assertEqual(img.shape[2], 3) # RGB

	def test_read_from_sequence(self):
		reader = Reader("./resources/MASA_sequence/MASA_sequence_00196.jpg")
		img = reader.read(196)

		self.assertEqual(img.dtype, np.uint8)
		self.assertEqual(img.shape[2], 3) # RGB

	def test_read_from_large_dpx_sequence(self):
		reader = Reader("./resources/EF_VFX_04/EF_VFX_04_0094900.dpx")
		img = reader.read(93230)

		self.assertEqual(img.dtype, np.uint8)
		self.assertEqual(img.shape[2], 3) # RGB


	def test_metadata_from_mp4(self):
		reader = Reader("./resources/Mása - becsukjuk, nem latszik.mp4")

		self.assertEqual(reader.fps, 25.0)
		self.assertEqual(reader.first_frame, 0)
		self.assertGreater(reader.last_frame, 0)

		self.assertEqual( (reader.width, reader.height), (1280, 720) )
		self.assertIsInstance(reader.width, int)
		self.assertIsInstance(reader.height, int)

	def test_metadata_from_sequence(self):
		reader = Reader("./resources/MASA_sequence/MASA_sequence_00196.jpg")

		self.assertEqual(reader.fps, None)
		self.assertEqual(reader.first_frame, 196)
		self.assertEqual(reader.last_frame, 300)

		self.assertEqual( (reader.width, reader.height), (1280, 720) )
		self.assertIsInstance(reader.width, int)
		self.assertIsInstance(reader.height, int)

	def test_metadata_from_large_DPX_sequence(self):
		reader = Reader("./resources/EF_VFX_04/EF_VFX_04_0094900.dpx")

		self.assertEqual(reader.fps, None)
		self.assertEqual(reader.first_frame, 94900)
		self.assertEqual(reader.last_frame, 94901)

		self.assertEqual((reader.width, reader.height), (4096, 2480))
		self.assertIsInstance(reader.width, int)
		self.assertIsInstance(reader.height, int)

	# def test_metadata(self):
	# 	# width, and height from video
	# 	reader = Reader("./resources/Mása - becsukjuk, nem latszik.mp4")
	# 	width, height = reader.width, reader.height

	# 	self.assertEqual( (width, height), (1280, 720))
	# 	self.assertIsInstance( width, int)
	# 	self.assertIsInstance( height, int)

	# 	# width and height from image sequence
	# 	reader = Reader("./resources/MASA_sequence/MASA_sequence_00196.jpg")
	# 	width, height = reader.width, reader.height

	# 	self.assertEqual( (width, height), (1280, 720))
	# 	self.assertIsInstance( width, int)
	# 	self.assertIsInstance( height, int)





if __name__ == '__main__':
    unittest.main()