
# coding=utf-8

import codecs
import io
import logging
import math
import struct
import traceback

from enum import Enum
from pathlib import Path
from pprint import pprint

from formats.exif import EXIF
from formats.icc import ICCProfile
from formats.photoshop import Resource as PhotoshopResource, ResourceType as PhotoshopResourceType, PhotoshopError
from formats.structio import BytesStructIO
from formats.util import Bunch


logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def split_4bit(i):
	return ((i & 0xF0) >> 4, i & 0x0F)

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

	def read_markerseg(self, handle):
		l = max(struct.unpack(">H", handle.read(2))[0], 2) - 2
		logger.debug("Reading marker of length {} @ {}".format(l, handle.tell()))
		return handle.read(l)

	def read_blob(self, handle):
		return codecs.encode(self.read_markerseg(handle), "hex").decode("ascii")

	def parse_short(self, handle):
		handle.read(2)  # length, who cares
		return struct.unpack(">H", handle.read(2))[0]

	def parse_sof(self, handle):
		raw = io.BytesIO(self.read_markerseg(handle))
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

	def parse_sos(self, handle):
		raw = io.BytesIO(self.read_markerseg(handle))
		components = {}
		for i in range(ord(raw.read(1))):
			# selector, dc entropy dest, ac entropy dest
			(dc_entropy, ac_entropy) = split_4bit(ord(raw.read(1)))
			components[ord(raw.read(1))] = {"dc_entropy": dc_entropy, "ac_entropy": ac_entropy}
		spectral_selection = ord(raw.read(1))
		end_of_spectral = ord(raw.read(1))
		(bit_high, bit_low) = split_4bit(ord(raw.read(1)))
		return {"components": components, "spectral_selection": spectral_selection, "end_of_spectral": end_of_spectral, "bit_high": bit_high, "bit_low": bit_low}

	def parse_jfif_app0(self, name, handle):
		(version, units, x_dens, y_dens, x_thumb, y_thumb) = struct.unpack(">2sBHHBB", handle.read(9))
		dat = {"version": "{}.{}".format(version[0], version[1]), "units": Units(units), "x_density": x_dens, "y_density": y_dens}
		thumb_res = (3 * (x_thumb * y_thumb))
		if thumb_res > 0:
			dat['width_thumb'] = x_thumb
			dat['height_thumb'] = y_thumb
			dat['thumb'] = handle.read(thumb_res)
		return dat

	def parse_app(self, handle):
		parsed = self.read_markerseg(handle)
		raw = BytesStructIO(parsed)
		try:
			name = raw.read_string().strip()
		except EOFError:
			return parsed
		try:
			return Marker.app_handlers[self][name](self, name, raw)
		except KeyError:
			return parsed

	def parse_exif(self, name, raw):
		raw.seek(1, io.SEEK_CUR)
		logger.debug("Found Exif APP1 data!")
		return EXIF.from_buffer(raw)

	def parse_xmp(self, name, raw):
		if name == b"XMP":
			domain = raw.read_string()
		else:
			domain = name
		logger.debug("Found XMP ({}) APP1 data!".format(domain))
		self.xmp = raw.read()

	def parse_iccp(self, name, raw):
		raw.seek(2, io.SEEK_CUR)  # there's two junk bytes? they might mean something just don't know
		return ICCProfile.parse(raw.read())

	def parse_photoshop(self, name, raw):
		resources = []
		while True:
			try:
				if raw.tell() >= len(raw.getvalue()):
					break
				resource = PhotoshopResource.from_structio(raw)
				if resource.id != PhotoshopResourceType.Thumbnail4_0 and resource.id != PhotoshopResourceType.Thumbnail5_0:
					resources.append(resource)
			except PhotoshopError:
				pass
		return resources

	def parse_photoshop_web(self, name, raw):
		param = {}
		param['quality'] = raw.read_uint()
		param['comment'] = raw.read_string()
		param['copyright'] = raw.read_string()
		return param

	def handler(self, handle):
		if self in Marker.handlers:
			return Marker.handlers[self](self, handle)

	@classmethod
	def reset(self):
		# TODO: not this, make Marker have a reference to JFIF instead?
		self.icc = b""
		self.photoshop = b""

	def append_iccp(self, name, raw):
		Marker.icc += raw.read()

	def append_photoshop(self, name, raw):
		Marker.photoshop += raw.read()

	def parse_adobe(self, name, raw):
		(version, flags0, flags1, color_transform) = struct.unpack(">BHHB", raw.read(6))
		return {"version": version, "flags0": flags0, "flags1": flags1, "color_transform": color_transform}

	@classmethod
	def finalize(self, jfif):
		if len(Marker.icc) > 0:
			jfif.icc = self.parse_iccp(self, "", BytesStructIO(Marker.icc))
		if len(Marker.photoshop) > 0:
			jfif.photshop = self.parse_photoshop(self, "", BytesStructIO(Marker.photoshop))


Marker.handlers = {
	Marker.DHT: Marker.read_blob,
	Marker.DQT: Marker.read_blob,
	Marker.DRI: Marker.parse_short,
	Marker.SOS: Marker.parse_sos,
	Marker.DNL: Marker.parse_short,
	Marker.COM: Marker.read_markerseg
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

for i in Marker.SOF:
	Marker.handlers[i] = Marker.parse_sof

Marker.APP = [
	Marker.APP0,
	Marker.APP1,
	Marker.APP2,
	Marker.APP3,
	Marker.APP5,
	Marker.APP6,
	Marker.APP7,
	Marker.APP9,
	Marker.APP10,
	Marker.APP11,
	Marker.APP12,
	Marker.APP13,
	Marker.APP14,
	Marker.APP15,
]

for i in Marker.APP:
	Marker.handlers[i] = Marker.parse_app


Marker.app_handlers = {
	Marker.APP0: {
		b"JFIF": Marker.parse_jfif_app0
	},
	Marker.APP1: {
		b"Exif": Marker.parse_exif,
		b"http://ns.adobe.com/xap/1.0/": Marker.parse_xmp,
		b"http://ns.adobe.com/xmp/extension/": Marker.parse_xmp,
		b"XMP": Marker.parse_xmp
	},
	Marker.APP2: {
		b"ICC_PROFILE": Marker.append_iccp
	},
	Marker.APP12: {
		b"Ducky": Marker.parse_photoshop_web
	},
	Marker.APP13: {
		b"Photoshop 3.0": Marker.append_photoshop
	},
	Marker.APP14: {
		b"Adobe": Marker.parse_adobe
	}
}


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
	DONE_ON_SCAN = False

	def __init__(self, handle):
		Marker.reset()
		self.markers = []
		with handle as self.handle:
			self.parse()

		Marker.finalize(self)

		del self.handle

	def marker_parser(self):
		while True:
			c = ord(self.handle.read(1)) # Read marker start
			if c == 0xFF:
				c = ord(self.handle.read(1)) # Read marker id
				try:
					yield Marker(c) # Read all of marker
				except (KeyError, ValueError):
					logger.error("Found invalid marker '{}'.".format(c))
					self.handle.seek(-2, io.SEEK_CUR) # Seek back after bad marker
					break
			else:
				logger.error("Found some random crap '{}' @ {}".format(c, self.handle.tell() - 1))
				self.handle.seek(-1, io.SEEK_CUR) # Seek back after reading crap byte
				break

	def parse(self):
		for marker in self.marker_parser():
			logger.debug(marker)
			try:
				parsed = Marker.handler(marker, self.handle)
			except Exception as e:
				logger.error("Failed to parse {} due to:\n{}".format(marker, traceback.format_exc(e)))
				continue
			self.markers.append((marker, parsed))
			if marker == Marker.EOI:
				break
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
		pprint(jfif)
	elif root.is_dir():
		for file in root.glob("**/*.jpg"):
			logger.info(file)
			jfif = JFIF.from_file(str(file))
			pprint(jfif)
	# logger.debug(jfif)

if __name__ == '__main__':
	main()
