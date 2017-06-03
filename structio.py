
# coding=utf-8

import io
import struct

from enum import Enum


class Endianess(Enum):
	BIG = 0xFEFF
	LITTLE = 0xFFFE

	def to_struct(self):
		return ">" if self == Endianess.BIG else "<"


class StructIO(io.RawIOBase):
	"""
	Based on SourceQueryPacket from SourceLib
	"""
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.set_endian(Endianess.BIG)

	def set_endian(self, endian):
		endian = endian.to_struct()
		self.CHAR = struct.Struct(endian + "c")
		self.BOOL = struct.Struct(endian + "?")
		self.UBYTE = struct.Struct(endian + "B")
		self.BYTE = struct.Struct(endian + "b")
		self.USHORT = struct.Struct(endian + "H")
		self.SHORT = struct.Struct(endian + "h")
		self.UINT = struct.Struct(endian + "I")
		self.INT = struct.Struct(endian + "i")
		self.ULONG = struct.Struct(endian + "L")
		self.LONG = struct.Struct(endian + "l")
		self.ULONGLONG = struct.Struct(endian + "Q")
		self.LONGLONG = struct.Struct(endian + "q")
		self.FLOAT = struct.Struct(endian + "f")
		self.DOUBLE = struct.Struct(endian + "d")

	def read_byte(self):
		return self.BYTE.unpack(self.read(1))[0]

	def read_ubyte(self):
		return self.UBYTE.unpack(self.read(1))[0]

	def read_char(self):
		return self.CHAR.unpack(self.read(1))[0]

	def read_bool(self):
		return self.BOOL.unpack(self.read(1))[0]

	def read_short(self):
		return self.SHORT.unpack(self.read(2))[0]

	def read_ushort(self):
		return self.USHORT.unpack(self.read(2))[0]

	def read_int(self):
		return self.INT.unpack(self.read(4))[0]

	def read_uint(self):
		return self.UINT.unpack(self.read(4))[0]

	def read_long(self):
		return self.LONG.unpack(self.read(4))[0]

	def read_ulong(self):
		return self.ULONG.unpack(self.read(4))[0]

	def read_float(self):
		return self.FLOAT.unpack(self.read(4))[0]

	def read_longlong(self):
		return self.LONGLONG.unpack(self.read(8))[0]

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

	def read_string_len(self, strlen):
		return self.read(strlen).replace("\x00", "").decode('utf-8', errors='replace')

	def write_byte(self, data):
		self.write(self.BYTE.pack(data))

	def write_char(self, data):
		self.write(self.CHAR.pack(data))

	def write_short(self, data):
		self.write(self.SHORT.pack(data))

	def write_long(self, data):
		self.write(self.LONG.pack(data))

	def write_float(self, data):
		self.write(self.FLOAT.pack(data))

	def write_longlong(self, data):
		self.write(self.LONGLONG.pack(data))

	def write_string(self, data):
		self.write(data.encode('utf-8') + "\x00")


class BytesStructIO(io.BytesIO, StructIO):
	pass


class FileStructIO(io.FileIO, StructIO):
	pass
