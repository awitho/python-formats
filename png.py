
# coding=utf-8

import zlib
import sys
import pdb
import struct

from enum import Enum
from pathlib import Path

from structio import BytesStructIO
from icc import ICCProfile


class ParseError(Exception):
	pass


class ChunkParseError(ParseError):
	pass


class CRCError(ParseError):
	pass

BYTE = struct.Struct(">B")
SHORT = struct.Struct(">H")
INT = struct.Struct(">I")
RGB8 = struct.Struct(">BBB")
RGB16 = struct.Struct(">HHH")


class PNG:
	MAGIC = b"\211PNG\r\n\032\n"

	KNOWN_TAGS = set([
		# PNG 1.2
		# http://www.libpng.org/pub/png/spec/1.2/png-1.2-pdg.html
		'IHDR',
		'PLTE',
		'IDAT',
		'IEND',
		'tRNS',
		'cHRM',
		'gAMA',
		'iCCP',
		'sBIT',
		'sRGB',
		'tEXt',
		'zTXt',
		'iTXt',
		'bKGD',
		'hIST',
		'pHYs',
		'sPLT',
		'tIME',

		# PNGEXT v1.2.0
		# http://www.libpng.org/pub/png/spec/register/pngext-1.4.0-pdg.html
		'fRAc',
		'gIFg',
		'gIFx',
		'gIFt',
		'oFFs',
		'pCAL',
		'sCAL',

		# PNGEXT v1.3.0
		# http://www.libpng.org/pub/png/spec/register/pngext-1.4.0-pdg.html
		'sTER',

		# PNGEXT v1.4.0
		# http://www.libpng.org/pub/png/spec/register/pngext-1.4.0-pdg.html
		'dSIG',

		# APNG
		# https://wiki.mozilla.org/APNG_Specification
		'acTL',
		'fcTL',
		'fdAT',

		# EXIF
		# http://www.cipa.jp/std/documents/e/DC-008-Translation-2016-E.pdf
		'exIf',
		'zxIf'

		# XMP
		# https://www.adobe.com/devnet/xmp.html
		'tXMP',

		# Unknown/Private Chunks
		# http://www.sno.phy.queensu.ca/~phil/exiftool/TagNames/PNG.html
		'vpAg',

		# Adobe Fireworks
		'prVW',
		'mkBF',
		'mkBT',
		'mkBS',
		'mkTS',

		# Apple iOS/Mac OS
		'iDOT',

		# GLDPNG Related
		'tpNG',  # 000000004A80291F crcs to 474C4433 or in ASCII "GLD3"

		# OLE Embed, Unsure as to origin
		'cpIp',

		# Corrupted IEND
		'IENT',
		'IEN5',
		'IENq'
	])

	FIFTH_BIT = 0b00100000

	VALID_ASCII = set().union(range(65, 90 + 1), range(97, 122 + 1))
	VERIFY = False

	class ColorType(Enum):
		GRAYSCALE = 0
		RGB = 2
		PALETTE = 3
		LA = 4
		RGBA = 6

	VALID_BIT_DEPTHS = {
		ColorType.GRAYSCALE: [1, 2, 4, 8, 16],
		ColorType.RGB: [8, 16],
		ColorType.PALETTE: [1, 2, 4, 8],
		ColorType.LA: [8, 16],
		ColorType.RGBA: [8, 16]
	}

	class Chunk:
		class Flags:
			def __init__(self, ancillary, private, reserved, safe):
				self.ancillary = ancillary
				self.private = private
				self.reserved = reserved
				self.safe = safe

			def __str__(self):
				return ",".join([key for (key, value) in self.__dict__.items() if value])

		def __init__(self, png=None, length=None, cid=None, data=None, crc=None):
			self.png = png
			self.length = length
			self.cid = cid
			self.data = data
			self.crc = crc
			self.meta = None

		@property
		def cid(self):
			return self._cid

		@cid.setter
		def cid(self, value):
			for i in value:
				if i not in PNG.VALID_ASCII:
					raise ParseError("invalid chunk type {}".format(repr(value)))
			self._cid = value

		@property
		def flags(self):
			return PNG.Chunk.Flags(*[(c & PNG.FIFTH_BIT) == PNG.FIFTH_BIT for c in self._cid])

		@property
		def cname(self):
			return self._cid.decode('ascii')

		def verify(self):
			return zlib.crc32(self.data, zlib.crc32(self.cid)) == self.crc

		def decode(self):
			handler = getattr(Chunks, self.cname)
			chunk = handler.parse(self.png, self)
			if not chunk.verify():
				raise ChunkParseError("invalid chunk {}".format(chunk))
			return chunk

		def __str__(self):
			return "<PNG.Chunk '{}' {}>".format(self.cname, self.flags)

	def __init__(self, path):
		self.file = Path(path) if not isinstance(path, Path) else path
		self.fp = self.file.open('rb')
		self.stat = self.file.stat()
		self.meta = None
		if self.fp.read(8) != PNG.MAGIC:
			raise ParseError("not a png?")

	def __enter__(self):
		return self

	def __exit__(self, one, two, three):
		self.close()

	def close(self):
		self.fp.close()

	def _get_chunk(self):
		length = int.from_bytes(self.fp.read(4), byteorder='big')
		return PNG.Chunk(self, length, self.fp.read(4), self.fp.read(length), int.from_bytes(self.fp.read(4), byteorder='big'))

	def chunks(self):
		chunk = self._get_chunk()
		if chunk.cname != "IHDR":
			raise ParseError("first chunk was not IHDR")

		seen_idata = False

		while True:
			if PNG.VERIFY and not chunk.verify():
				raise CRCError("bad crc {}".format(chunk.cname))

			yield chunk

			if chunk.cname == 'IEND':
				break
			elif chunk.cname == 'IDAT':
				seen_idata = True

			if self.fp.tell() == self.stat.st_size:
				raise ParseError("reached end of file without IEND")
				break

			chunk = self._get_chunk()

		if not seen_idata:
			raise ParseError("did not find any IDATA chunks")

		if self.fp.tell() != self.stat.st_size:
			print("{} has trailing data!".format(self.file))


class CompressionMethod(Enum):
	DEFLATE = 0


class Chunks:
	class Base:
		def __init__(self, raw):
			self.raw = raw

		@classmethod
		def parse(self, png, chunk):
			if chunk.length != self.STRUCT.size:
				raise ChunkParseError("invalid chunk length for chunk {}".format(self.cname))
			return self(*self.STRUCT.unpack(chunk.data), chunk)

		def verify(self):
			return True

		@property
		def cname(self):
			return type(self).__name__

		def __str__(self):
			return str(self.__dict__)

	class IHDR(Base):
		STRUCT = struct.Struct(">2I5B")

		def __init__(self, width, height, bit_depth, color_type, compression, filter_type, interlace, *args):
			super().__init__(*args)

			self.width = width
			self.height = height
			self.bit_depth = bit_depth
			self.color_type = PNG.ColorType(color_type)
			self.compression = compression
			self.filter_type = filter_type
			self.interlace = interlace

		def verify(self):
			return (self.bit_depth == 1 or self.bit_depth % 2 == 0) and self.bit_depth in PNG.VALID_BIT_DEPTHS[self.color_type]

	class PLTE(Base):
		def __init__(self, palette, *args):
			super().__init__(*args)

			self.palette = palette

		@classmethod
		def parse(self, png, chunk):
			if chunk.length % 3 != 0:
				raise ChunkParseError("PLTE chunk length is not divisible by 3.")
			return self([RGB8.unpack(chunk.data[i:i + 3]) for i in range(0, chunk.length, 3)], chunk)

	class tRNS(Base):
		def __init__(self, transparency, *args):
			super().__init__(*args)

			self.transparency = transparency

		@classmethod
		def parse(self, png, chunk):
			if png.meta.color_type == PNG.ColorType.GRAYSCALE:
				if chunk.length != 2:
					raise ChunkParseError("invalid length for tRNS with color type {}".format(png.meta.color_type))
				return self(SHORT.unpack(chunk.data))
			elif png.meta.color_type == PNG.ColorType.RGB:
				if chunk.length % 3 != 0:
					raise ChunkParseError("invalid length for tRNS with color type {}".format(png.meta.color_type))
				return self([RGB8.unpack(chunk.data[i:i + 3] for i in range(0, chunk.length, 3))])
			elif png.meta.color_type == PNG.ColorType.PALETTE:
				return self([BYTE.unpack(chunk.data[i]) for i in range(chunk.length)])
			else:
				raise ChunkParseError("tRNS is an invalid chunk for color type {}".format(png.meta.color_type))

	class gAMA(Base):
		STRUCT = INT

		def __init__(self, gamma, *args):
			super().__init__(*args)

			self.gamma = gamma

	class cHRM(Base):
		STRUCT = struct.Struct(">8I")
		DIVISOR = 100000

		def __init__(self, white_x, white_y, red_x, red_y, green_x, green_y, blue_x, blue_y, *args):
			super().__init__(*args)

			self.white_x = white_x / self.DIVISOR
			self.white_y = white_y / self.DIVISOR
			self.red_x = red_x / self.DIVISOR
			self.red_y = red_y / self.DIVISOR
			self.green_x = green_x / self.DIVISOR
			self.green_y = green_y / self.DIVISOR
			self.blue_x = blue_x / self.DIVISOR
			self.blue_y = blue_y / self.DIVISOR

	class sRGB(Base):
		STRUCT = BYTE

		def __init__(self, intent, *args):
			super().__init__(*args)

			if intent not in range(0, 3 + 1):
				raise ChunkParseError("invalid intent for sRGB")
			self.intent = intent

	class tEXt(Base):
		def __init__(self, key, text, *args):
			super().__init__(*args)

			self.key = key.decode('latin-1')
			self.text = text.decode('latin-1')

		@classmethod
		def parse(self, png, chunk):
			(name, rest) = chunk.data.split(b"\0", maxsplit=1)
			return self(name, rest, chunk)

	class zTXt(tEXt):
		@classmethod
		def parse(self, png, chunk):
			(name, rest) = chunk.data.split(b"\0", maxsplit=1)
			method = CompressionMethod(BYTE.unpack(rest[:1])[0])
			if method == CompressionMethod.DEFLATE:
				data = zlib.decompress(rest[1:])
			return self(name, data, chunk)

	class iCCP(zTXt):
		def __init__(self, key, text, *args):
			self.key = key.decode('latin-1')
			self.profile = ICCProfile.parse(text)

	class iTXt(Base):
		def __init__(self, key, flag, method, language, translated, text):
			self.key = key
			self.flag = flag
			self.method = method
			self.language = language
			self.translated = translated
			self.text = text

		@classmethod
		def parse(self, png, chunk):
			data = BytesStructIO(chunk.data)
			itxt = self(data.read_string().decode('utf-8'), data.read_bool(), CompressionMethod(data.read_ubyte()), data.read_string().decode('utf-8'), data.read_string().decode('utf-8'), data.read())
			if itxt.flag and itxt.method == CompressionMethod.DEFLATE:
				itxt.text = zlib.decompress(itxt.text)
			itxt.text = itxt.text.decode('utf-8')
			return itxt


UNKNOWN_TAGS = set([
	'cmOD',
	'iDOT',
	'cpIp',
	'tpNG',
	'meTa'
])


def main():
	import argparse
	import traceback

	from pathlib import Path

	from lxml import etree

	parser = argparse.ArgumentParser()
	parser.add_argument("file")
	args = parser.parse_args()

	PNG.VERIFY = True
	png = PNG(args.file)
	try:
		chunks = png.chunks()
		while True:
			try:
				chunk = next(chunks)
			except StopIteration:
				break
			if chunk.cid == "exIF":
				print(chunk)
	except AttributeError:
		return
	except ParseError as e:
		print("Failed on {}: {}".format(file, e.args[0]))
		return
	finally:
		png.close()

if __name__ == '__main__':
	main()
