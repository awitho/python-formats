
# coding=utf-8

import io
import struct

from enum import Enum


class Endianess(Enum):
	BIG = 0xFEFF
	LITTLE = 0xFFFE

	def get_structs(self):
		return Endianess.structs[self]

Endianess.structs = {
	Endianess.BIG: {
		"char": struct.Struct(">c"),
		"bool": struct.Struct(">?"),
		"ubyte": struct.Struct(">B"),
		"byte": struct.Struct(">b"),
		"ushort": struct.Struct(">H"),
		"short": struct.Struct(">h"),
		"uint": struct.Struct(">I"),
		"int": struct.Struct(">i"),
		"ulong": struct.Struct(">L"),
		"long": struct.Struct(">l"),
		"ulonglong": struct.Struct(">Q"),
		"longlong": struct.Struct(">q"),
		"float": struct.Struct(">f"),
		"double": struct.Struct(">d"),
	},
	Endianess.LITTLE: {
		"char": struct.Struct("<c"),
		"bool": struct.Struct("<?"),
		"ubyte": struct.Struct("<B"),
		"byte": struct.Struct("<b"),
		"ushort": struct.Struct("<H"),
		"short": struct.Struct("<h"),
		"uint": struct.Struct("<I"),
		"int": struct.Struct("<i"),
		"ulong": struct.Struct("<L"),
		"long": struct.Struct("<l"),
		"ulonglong": struct.Struct("<Q"),
		"longlong": struct.Struct("<q"),
		"float": struct.Struct("<f"),
		"double": struct.Struct("<d"),
	}
}


class StructIO(io.RawIOBase):
	"""
	Based on SourceQueryPacket from SourceLib
	"""

	def __init__(self, *args, endian=Endianess.BIG, **kwargs):
		"""
		This never gets called because io.BytesIO and io.FileIO never call super...
		"""
		super().__init__()
		self.set_endian(endian)

	def set_endian(self, endian):
		self.structs = endian.get_structs()

	def read_byte(self):
		return self.structs["byte"].unpack(self.read(1))[0]

	def read_ubyte(self):
		return self.structs["ubyte"].unpack(self.read(1))[0]

	def read_char(self):
		return self.structs["char"].unpack(self.read(1))[0]

	def read_bool(self):
		return self.structs["bool"].unpack(self.read(1))[0]

	def read_short(self):
		return self.structs["short"].unpack(self.read(2))[0]

	def read_ushort(self):
		return self.structs["ushort"].unpack(self.read(2))[0]

	def read_int(self):
		return self.structs["int"].unpack(self.read(4))[0]

	def read_uint(self):
		return self.structs["uint"].unpack(self.read(4))[0]

	def read_long(self):
		return self.structs["long"].unpack(self.read(4))[0]

	def read_ulong(self):
		return self.structs["ulong"].unpack(self.read(4))[0]

	def read_float(self):
		return self.structs["float"].unpack(self.read(4))[0]

	def read_longlong(self):
		return self.structs["longlong"].unpack(self.read(8))[0]

	def read_string(self):
		start = self.tell()
		while True:
			c = self.read(1)
			if len(c) == 0:
				raise EOFError()
			if c == b'\x00':
				end = self.tell() - 1
				break
		return self.getvalue()[start:end]

	def read_string_len(self, strlen, codec="utf-8"):
		return self.read(strlen).replace("\x00", "").decode(codec, errors='replace')

	def write_byte(self, data):
		self.write(self.structs["byte"].pack(data))

	def write_char(self, data):
		self.write(self.structs["char"].pack(data))

	def write_short(self, data):
		self.write(self.structs["short"].pack(data))

	def write_long(self, data):
		self.write(self.structs["long"].pack(data))

	def write_float(self, data):
		self.write(self.structs["float"].pack(data))

	def write_longlong(self, data):
		self.write(self.structs["longlong"].pack(data))

	def write_string(self, data, codec="utf-8"):
		self.write(data.encode(codec) + "\x00")


class BytesStructIO(io.BytesIO, StructIO):
	def __init__(self, *args, **kwargs):
		# sigh...
		# please use super() io.BytesIO
		io.BytesIO.__init__(self, *args, **kwargs)
		StructIO.__init__(self, *args, **kwargs)


class FileStructIO(io.FileIO, StructIO):
	def __init__(self, *args, **kwargs):
		# sigh...
		# please use super()
		io.FileIO.__init__(self, *args, **kwargs)
		StructIO.__init__(self, *args, **kwargs)
