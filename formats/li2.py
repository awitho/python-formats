import struct
import logging
import io

from pprint import pprint
from pathlib import Path

from structio import FileStructIO, Endianess

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class BOD(object):
	def __init__(self, path):
		self.files = []
		with FileStructIO(path, endian=Endianess.LITTLE) as self.handle:
			hit_entries = False
			while not hit_entries:
				s = self.handle.read(4)
				self.handle.seek(-4, io.SEEK_CUR)
				if s == b"DIRY" or s == b"FILE":
					hit_entries = True
					continue

				self.files.append({"name": self.handle.read_string().decode("ascii")})

			count = 0
			while count < len(self.files):
				ref = self.files[count]
				ref['type'] = self.handle.read(4)
				ref['size'] = self.handle.read_uint()
				ref['offset'] = self.handle.read_uint()
				ref['unk1'] = self.handle.read_uint()

				count += 1

		for f in self.files:
			if f['type'] == b"FILE":
				print(f)

		del self.handle

def main():
	import argparse
	parser = argparse.ArgumentParser()
	parser.add_argument("-D", "--debug", action="store_true")
	parser.add_argument("-d", "--directory", action="store_true")
	parser.add_argument("file")
	args = parser.parse_args()

	if args.debug:
		logger.setLevel(logging.DEBUG)

	root = Path(args.file)
	if not root.exists():
		logger.debug("What?")
		return

	if root.is_file():
		jfif = BOD(str(root))
	#elif root.is_dir():
	#	for file in root.glob("**/*.jpg"):
	#		logger.info(file)
	#		jfif = JFIF.from_file(str(file))
	#		pprint(jfif)
	# logger.debug(jfif)

if __name__ == '__main__':
	main()
