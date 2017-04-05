
# coding=utf-8

import datetime
import struct

from structio import BytesStructIO


class ICCException(Exception):
	pass


class ICCParseException(ICCException):
	pass


class ICCProfile:
	VERSION = "4.3"
	MAGIC = b'acsp'

	class Datetime:
		STRUCT = struct.Struct(">6H")

		@classmethod
		def parse(self, data):
			return datetime.datetime(*self.STRUCT.unpack(data))

	class XYZNumber:
		STRUCT = struct.Struct(">3f")

		def __init__(self, x, y, z):
			self.x = x
			self.y = y
			self.z = z

		@classmethod
		def parse(self, data):
			return self(*self.STRUCT.unpack(data))

		def __str__(self):
			return "{}:{}:{}".format(self.x, self.y, self.z)

		def __repr__(self):
			return str(self)

	class Header:
		STRUCT = struct.Struct(">I4sI4s4s4s12s4s4sI4s4sQI12s4s16s28s")

		def __init__(self, size, cmm_type, version, dev_class, color_space, pcs, datetime, magic, platform, flags, manufacturer, model, attributes, intent, illuminant, creator, id, reserved):
			self.size = size
			self.cmm_type = cmm_type
			self.version = version
			self.dev_class = dev_class
			self.color_space = color_space
			self.pcs = pcs
			self.datetime = datetime
			self.magic = magic
			self.platform = platform
			self.flags = flags
			self.manufacturer = manufacturer
			self.model = model
			self.attributes = attributes
			self.intent = intent
			self.illuminant = illuminant
			self.creator = creator
			self.id = id

		@classmethod
		def parse(self, data):
			header = self(*self.STRUCT.unpack(data))
			header.datetime = ICCProfile.Datetime.parse(header.datetime)
			header.illuminant = ICCProfile.XYZNumber.parse(header.illuminant)
			return header

		def __str__(self):
			return str(self.__dict__)

	def __init__(self, header):
		self.header = header

	@classmethod
	def parse(self, data):
		if data[36:40] != ICCProfile.MAGIC:
			raise ICCParseException("not an ICC profile?")
		data = BytesStructIO(data)
		header = ICCProfile.Header.parse(data.read(128))
		tag_count = data.read_uint()
		print(tag_count)
		return self(header)
