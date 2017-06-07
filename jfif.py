
# coding=utf-8

import io
import logging
import math
import struct

from enum import Enum
from pathlib import Path
from pprint import pprint

from exif import EXIF
from photoshop import Resource as PhotoshopResource, ResourceType as PhotoshopResourceType, PhotoshopError
from structio import BytesStructIO
from util import Bunch

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def split_4bit(i):
	return ((i & 0xF0) >> 4, i & 0x0F)

def read_markerseg(handle):
	l = max(struct.unpack(">H", handle.read(2))[0], 2) - 2
	logger.debug("Reading marker of length {} @ {}".format(l, handle.tell()))
	return handle.read(l)

def read_nulstring(s, start=0):
	for i in range(start, len(s)):
		if s[i:i + 1] == b'\x00':
			end = i
			break
	return s[start:end]


class Units(Enum):
	PIXEL = 0
	DPI = 1
	DPC = 2


class Marker(Enum):
	# Start of Frame
	# non-diff, huffman
	SOF0 = 0xC0  # start of frame 0
	SOF1 = 0xC1  # ...
	SOF2 = 0xC2
	SOF3 = 0xC3
	# Who knows what happened to SOF4?
	# diff, huffman
	SOF5 = 0xC5
	SOF6 = 0xC6
	SOF7 = 0xC7
	# non-diff, arithmetic
	JPG = 0xC8  # reserved for jpeg extension
	SOF9 = 0xC9
	SOF10 = 0xCA
	SOF11 = 0xCB
	# diff, arithmetic
	SOF13 = 0xCD
	SOF14 = 0xCE
	SOF15 = 0xCF
	# huffman specs
	DHT = 0xC4  # define huffman table
	# arithmetic coding conditioning specs
	DAC = 0xCC  # define arithmetic conditiong
	# restart internval termination (no segment)
	RST0 = 0xD0
	RST1 = 0xD1
	RST2 = 0xD2
	RST3 = 0xD3
	RST4 = 0xD4
	RST5 = 0xD5
	RST6 = 0xD6
	RST7 = 0xD7
	# other
	SOI = 0xD8  # start of image
	EOI = 0xD9  # end of image
	SOS = 0xDA  # start of scan
	DQT = 0xDB  # define quantization table
	DNL = 0xDC  # define number of lines
	DRI = 0xDD  # define restart interval
	DHP = 0xDE  # define hierarchical progression
	EXP = 0xDF  # expand reference component
	# app segments
	APP0 = 0xE0
	APP1 = 0xE1
	APP2 = 0xE2
	APP3 = 0xE3
	APP4 = 0xE4
	APP5 = 0xE5
	APP6 = 0xE6
	APP7 = 0xE7
	APP8 = 0xE8
	APP9 = 0xE9
	APP10 = 0xEA
	APP11 = 0xEB
	APP12 = 0xEC
	APP13 = 0xED
	APP14 = 0xEE
	APP15 = 0xEF
	# reserved extensions
	JPG0 = 0xF0
	JPG1 = 0xF1
	JPG2 = 0xF2
	JPG3 = 0xF3
	JPG4 = 0xF4
	JPG5 = 0xF5
	JPG6 = 0xF6
	JPG7 = 0xF7
	JPG8 = 0xF8
	JPG9 = 0xF9
	JPG10 = 0xFA
	JPG11 = 0xFB
	JPG12 = 0xFC
	JPG13 = 0xFD
	# reserved extensions end
	COM = 0xFE  # comment

	@staticmethod
	def parse_short(handle):
		handle.read(2)  # length, who cares
		return struct.unpack(">H", handle.read(2))[0]

	@staticmethod
	def parse_sof(handle):
		raw = io.BytesIO(read_markerseg(handle))
		sample_precision = struct.unpack(">B", raw.read(1))[0]
		lines = struct.unpack(">H", raw.read(2))[0]
		samples_per_line = struct.unpack(">H", raw.read(2))[0]
		components = {}
		for i in range(ord(raw.read(1))):
			id = ord(raw.read(1))
			(h_sample, v_sample) = split_4bit(ord(raw.read(1)))
			quant_dest = ord(raw.read(1))

			components[id] = {"h_sample": h_sample, "v_sample": v_sample, "quant_dest": quant_dest}
		return {"sample_precision": sample_precision, "lines": lines, "samples_per_line": samples_per_line, "components": components}

	@staticmethod
	def parse_sos(handle):
		raw = io.BytesIO(read_markerseg(handle))
		components = {}
		for i in range(ord(raw.read(1))):
			# selector, dc entropy dest, ac entropy dest
			(dc_entropy, ac_entropy) = split_4bit(ord(raw.read(1)))
			components[ord(raw.read(1))] = {"dc_entropy": dc_entropy, "ac_entropy": ac_entropy}
		spectral_selection = ord(raw.read(1))
		end_of_spectral = ord(raw.read(1))
		(bit_high, bit_low) = split_4bit(ord(raw.read(1)))
		return {"components": components, "spectral_selection": spectral_selection, "end_of_spectral": end_of_spectral, "bit_high": bit_high, "bit_low": bit_low}

	@staticmethod
	def parse_jfif_app0(handle):
		(version, units, x_dens, y_dens, x_thumb, y_thumb) = struct.unpack(">2sBHHBB", handle.read(9))
		dat = {"version": "{}.{}".format(version[0], version[1]), "units": Units(units), "x_density": x_dens, "y_density": y_dens}
		thumb_res = (3 * (x_thumb * y_thumb))
		if thumb_res > 0:
			dat['width_thumb'] = x_thumb
			dat['height_thumb'] = y_thumb
			dat['thumb'] = handle.read(thumb_res)
		return dat

	@classmethod
	def handler(cls, marker, handle):
		if marker in cls.handlers:
			return cls.handlers[marker](handle)

Marker.handlers = {
	Marker.APP0: read_markerseg,
	Marker.APP1: read_markerseg,
	Marker.APP2: read_markerseg,
	Marker.APP3: read_markerseg,
	Marker.APP4: read_markerseg,
	Marker.APP5: read_markerseg,
	Marker.APP6: read_markerseg,
	Marker.APP7: read_markerseg,
	Marker.APP8: read_markerseg,
	Marker.APP9: read_markerseg,
	Marker.APP10: read_markerseg,
	Marker.APP11: read_markerseg,
	Marker.APP12: read_markerseg,
	Marker.APP13: read_markerseg,
	Marker.APP14: read_markerseg,
	Marker.APP15: read_markerseg,
	Marker.DHT: read_markerseg,
	Marker.DQT: read_markerseg,
	Marker.DRI: Marker.parse_short,
	Marker.SOS: Marker.parse_sos,
	Marker.SOF0: Marker.parse_sof,
	Marker.SOF1: Marker.parse_sof,
	Marker.SOF2: Marker.parse_sof,
	Marker.SOF3: Marker.parse_sof,
	Marker.SOF5: Marker.parse_sof,
	Marker.SOF6: Marker.parse_sof,
	Marker.SOF7: Marker.parse_sof,
	Marker.SOF9: Marker.parse_sof,
	Marker.SOF10: Marker.parse_sof,
	Marker.SOF11: Marker.parse_sof,
	Marker.SOF13: Marker.parse_sof,
	Marker.SOF14: Marker.parse_sof,
	Marker.SOF15: Marker.parse_sof,
	Marker.DNL: Marker.parse_short,
	Marker.COM: read_markerseg
}

Marker.SOF = [
	Marker.SOF0,
	Marker.SOF1,
	Marker.SOF2,
	Marker.SOF3,
	Marker.SOF5,
	Marker.SOF6,
	Marker.SOF7,
	Marker.SOF9,
	Marker.SOF10,
	Marker.SOF11,
	Marker.SOF13,
	Marker.SOF14,
	Marker.SOF15,
]


class JFIF(Bunch):
	"""
	Little Endian (MSB is left handed)
	All "parameters" are unsigned integers of varying size, 4 bit parameters are ALWAYS in pairs (4, 8 or 16-bit).
	Markers are two-byte patterns of FF followed by a byte in the range 00-FF (exclusive)
	Marker segments are preceded only by certain Markers and the first two bytes are the length of segment including the two byte length but not the Marker
	"""

	# this is useful as we don't usually care about any real data, all the metadata seems to happen before SOF
	DONE_ON_FRAME = True
	# done_on_frame will kill the loop before we even reach scan.
	DONE_ON_SCAN = True

	def __init__(self, handle):
		with handle as self.handle:
			self.parse()

		del self.handle

	def marker_parser(self):
		while True:
			c = ord(self.handle.read(1))
			if c == 0xFF:
				c = ord(self.handle.read(1))
				try:
					yield Marker(c)
				except (KeyError, ValueError):
					logger.error("Found invalid marker '{}'.".format(c))
					self.handle.seek(-2, io.SEEK_CUR)
					break
			else:
				logger.error("Found some random crap '{}' @ {}".format(c, self.handle.tell() - 1))
				self.handle.seek(-1, io.SEEK_CUR)
				break

	def parse(self):
		for marker in self.marker_parser():
			logger.debug(marker)
			parsed = Marker.handler(marker, self.handle)
			if marker == Marker.EOI:
				break
			elif marker == Marker.APP0:
				raw = BytesStructIO(parsed)
				try:
					name = raw.read_string().strip()
				except EOFError:
					continue
				if name == b"JFIF":
					logger.debug("Found JFIF APP0 data!")
					self.update(Marker.parse_jfif_app0(raw))
			elif marker == Marker.APP1:
				raw = BytesStructIO(parsed)
				name = raw.read_string().strip()
				if name == b"Exif":
					# padding byte...
					raw.seek(1, io.SEEK_CUR)
					logger.debug("Found Exif APP1 data!")
					self.exif = EXIF.from_buffer(raw)
					# pprint(exif)
				elif name == b"http://ns.adobe.com/xap/1.0/" or name == b"http://ns.adobe.com/xmp/extension/" or name == b"XMP":
					if name == b"XMP":
						domain = raw.read_string()
					else:
						domain = name
					logger.debug("Found XMP ({}) APP1 data!".format(domain))
					self.xmp = raw.read()
				else:
					logger.debug("unknown app1")
					logger.debug(parsed[0:128])
			elif marker == Marker.APP2:
				raw = BytesStructIO(parsed)
				name = raw.read_string().strip()
				if name == b"ICC_PROFILE":
					pass  # logger.debug("Found ICC Profile APP2 data.")
				else:
					logger.debug("unknown app2")
					logger.debug(parsed[0:128])
			elif marker == Marker.APP13:
				raw = BytesStructIO(parsed)
				name = raw.read_string().strip()
				if name == b"Photoshop 3.0":
					self.resources = []
					while True:
						try:
							if raw.tell() >= len(parsed):
								break
							resource = PhotoshopResource.from_structio(raw)
							if resource.id != PhotoshopResourceType.Thumbnail4_0 and resource.id != PhotoshopResourceType.Thumbnail5_0:
								self.resources.append(resource)
						except PhotoshopError:
							pass
				else:
					logger.debug("unknown app13")
					logger.debug(parsed[0:128])
			elif marker == Marker.APP14:
				raw = BytesStructIO(parsed)
				name = raw.read_string().strip()
				if name == b"Adobe":
					pass  # logger.debug("Found Adobe APP14 data!")
				else:
					logger.debug("unknown app14")
					logger.debug(parsed[0:128])
			elif marker == Marker.COM:
				self.comment = parsed
			elif marker in Marker.SOF:
				if JFIF.DONE_ON_FRAME:
					break

				self.update(parsed)
				hmax = 0
				vmax = 0
				for (i, component) in self.components.items():
					hmax = max(hmax, component['h_sample'])
					vmax = max(vmax, component['v_sample'])

				for (i, component) in self.components.items():
					component['x'] = math.ceil(self.lines * (component['h_sample'] / hmax))
					component['y'] = math.ceil(self.samples_per_line * (component['v_sample'] / vmax))

				self.data_unit_size = self.sample_precision // 8
			elif marker == Marker.SOS:
				# there are restart_interval mcus in one scan interval
				# if this does ever get implemented it should probably goto a c module for huffman, quantization and dct decoding (as python will assuredly be ULTRA slow at it)
				if JFIF.DONE_ON_SCAN:
					break

				while True:
					c0 = self.handle.read(1)
					if c0 == b"\xFF":
						c1 = ord(self.handle.read(1))
						if c1 >= 0xD0 and c1 <= 0xD7:
							continue
						elif c1 >= 0xC0:
							self.handle.seek(-2, io.SEEK_CUR)
							break

	@classmethod
	def from_file(cls, path):
		return cls(open(path, "rb"))

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
		jfif = JFIF.from_file(str(root))
		print(jfif)
	elif root.is_dir():
		for file in root.glob("**/*.jpg"):
			logger.info(file)
			jfif = JFIF.from_file(str(file))
			pprint(jfif)
	# logger.debug(jfif)

if __name__ == '__main__':
	main()
