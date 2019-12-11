
# coding=utf-8

import sys
import os

import io

from structio import FileStructIO, Endianess


class GMD(FileStructIO):
	MAGIC = b"\x00\x44\x4D\x47"

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

		header = self.read(0x4)
		if header == self.MAGIC:
			self.set_endian(Endianess.BIG)
		elif header == bytes(reversed(self.MAGIC)):
			self.set_endian(Endianess.LITTLE)
		else:
			raise Exception("Invalid MAGIC")

		self.version = self.read(0x4)
		if self.endian == Endianess.BIG:
			self.version = reversed(self.version)
		self.version = list(self.version)

		self.unknown1 = self.read(0x4)
		self.unknown2 = self.read(0x4)
		self.unknown3 = self.read(0x8)
		self.string_count = self.read_uint()
		self.unknown4 = self.read(0x4)
		self.table_len = self.read_uint()
		self.table_count = self.read_uint()

		self.seek(self.table_count + 1, io.SEEK_CUR)

		self.strings = [self.read_string().decode("utf-8") for i in range(self.string_count)]

	def __str__(self):
		return "<{} {}>".format(self.__class__.__name__, ".".join([str(i) for i in self.version]))

def main():
	import argparse
	from pprint import pprint
	parser = argparse.ArgumentParser()
	parser.add_argument("file")
	args = parser.parse_args()

	if not os.path.isfile(args.file):
		return 1

	gmd = GMD(args.file)
	print(gmd)
	print(gmd.string_count)
	print(gmd.table_len)
	print(gmd.table_count)
	if not False:
		for s in gmd.strings:
			print(s)
			print()

if __name__ == "__main__":
	sys.exit(main())
