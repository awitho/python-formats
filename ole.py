
# coding=utf-8

import io
import struct

from enum import Enum


class Color(Enum):
	RED = 0
	BLACK = 1


class FileBlockIO(io.FileIO):
	def __init__(self, *args, bsize=512, offset=0, **kwargs):
		super().__init__(*args, **kwargs)
		self.bsize = bsize
		self._offset = offset

	def seek(self, idx, *args, **kwargs):
		super().seek((idx + self._offset) * self.bsize, *args, **kwargs)

	def read(self, count=1, **kwargs):
		return super().read(count * self.bsize, **kwargs)

	def sector(self, idx):
		# print("SECTOR %s" % idx)
		self.seek(idx)
		return self.read()

	def offset(self, val):
		self._offset = val


class StreamView(object):
	def __init__(self, stream=None, handle=None, size=512):
		self.stream = [] if stream is None else stream
		self.handle = handle
		self.size = size
		self.pos = 0

	def read(self, size=None):
		if size is None:
			size = self.size

		start_stream_pos = max(0, self.pos // self.size)
		end_stream_pos = min(len(self.stream), (self.pos + size - 1) // self.size)
		# print("%s = %s:%s - %s" % (self.pos, start_stream_pos, end_stream_pos, len(self.stream)))

		buf = b''
		for i in range(start_stream_pos, end_stream_pos + 1):
			buf += self.sector(i)

		if len(buf) > size:
			i = (self.pos % self.size)
			# print("%s:%s = %s" % (i, i + size, i + size - i))
			buf = buf[i:i + size]
		self.pos += size
		return buf

	def sector(self, idx):
		return self.handle.sector(self.stream[idx])

	def has_more(self):
		return self.pos < (self.size * len(self.stream))


class OLEException(Exception):
	pass


class OLE:
	MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"

	class SectType(Enum):
		DIFSECT = 0xFFFFFFFC
		FATSECT = 0xFFFFFFFD
		ENDOFCHAIN = 0xFFFFFFFE
		FREESECT = 0xFFFFFFFF

	class FAT:
		STRUCT = struct.Struct("<128L")

		@classmethod
		def parse(self, data):
			return self.STRUCT.unpack(data)

	class MiniFAT:
		STRUCT = struct.Struct("<16L")

		@classmethod
		def parse(self, data):
			return self.STRUCT.unpack(data)

	class Directory:
		STRUCT = struct.Struct("<64sH2B3L16sI2Q2I2H")

		class Type(Enum):
			INVALID = 0
			STORAGE = 1
			STREAM = 2
			LOCKBYTES = 3
			PROPERTY = 4
			ROOT = 5

		def __init__(self, name, length, type, flags, left_sid, right_sid, child_sid, clsid, user_flags, ctime, mtime, start, size, props, filler):
			self.name = name
			self.length = length
			self.type = type
			self.flags = flags
			self.left_sid = left_sid
			self.left = None
			self.right_sid = right_sid
			self.right = None
			self.child_sid = child_sid
			self.child = None
			self.clsid = clsid
			self.user_flags = user_flags
			self.ctime = ctime
			self.mtime = mtime
			self.start = start
			self.size = size
			self.props = props

		def __str__(self):
			return "{} {}".format(self.name, self.type)

		def __repr__(self):
			return str(self)

		def __lt__(self, other):
			return len(self.name) < len(other.name)

		@classmethod
		def parse(self, data):
			d = self(*self.STRUCT.unpack(data))
			d.name = d.name.decode('utf-16le').split("\x00\x00", maxsplit=1)[0]
			d.type = OLE.Directory.Type(d.type)
			d.flags = Color(d.flags)
			return d

	class Header:
		STRUCT = struct.Struct("<8s16s6H10L109L")

		def __init__(self, magic, id, minor_version, dll_version, byteorder, sect_shift, minisect_shift, reserved, reserved1, reserved2, sect_count, first_sect, sig, minisectcutoff, minifatstart, minifatcount, difstart, difcount, *args):
			if magic != OLE.MAGIC:
				raise OLEException("invalid magic")
			self.id = id
			self.minor_version = minor_version
			self.dll_version = dll_version
			self.sect_size = pow(2, sect_shift)
			self.minisect_size = pow(2, minisect_shift)
			self.sect_count = sect_count
			self.sect_dir = first_sect
			self.sig = sig
			self.minisect_cutoff = minisectcutoff
			self.minifat_start = minifatstart
			self.minifat_count = minifatcount
			self.dif_start = difstart
			self.dif_count = difcount
			self.fats = args

		@classmethod
		def parse(self, data):
			return self(*self.STRUCT.unpack(data))

		def __str__(self):
			return str(self.__dict__)

	def __init__(self, handle=None, meta=None, fat=[], minifat=[], dirs=[]):
		self.handle = handle
		self.meta = meta
		self.fat = fat
		self.minifat = minifat
		self.dirs = dirs
		self.ministream = None

	def sid(self, sect):
		# print("SID %s" % sect)
		view = StreamView(handle=self.handle)

		while True:
			try:
				typ = OLE.SectType(sect)
				if typ == OLE.SectType.ENDOFCHAIN:
					break
				else:
					raise Exception("Hit an unexpected %s when browsing the FAT" % typ)
			except ValueError:
				pass
			view.stream.append(sect)
			sect = self.fat[sect]
		return view

	def minisid(self, sect):
		# print("MINISID %s" % sect)
		view = StreamView(handle=self.ministream, size=64)

		while True:
			try:
				typ = OLE.SectType(sect)
				if typ == OLE.SectType.ENDOFCHAIN:
					break
				else:
					raise Exception("Hit an unexpected %s when browsing the FAT" % typ)
			except ValueError:
				pass
			view.stream.append(sect)
			sect = self.minifat[sect]
		return view

	def __enter__(self):
		return self

	def __exit__(self, one, two, three):
		self.handle.close()

	def __str__(self):
		return str(self.__dict__)

	@classmethod
	def fromfile(self, path):
		data = FileBlockIO(path)
		ole = self(handle=data)
		ole.meta = OLE.Header.parse(data.sector(0))
		data.offset(1)

		for i in ole.meta.fats:
			if i == OLE.SectType.FREESECT.value:
				break
			ole.fat.extend(OLE.FAT.parse(data.sector(i)))
		del ole.meta.fats

		stream = ole.sid(ole.meta.sect_dir)
		while stream.has_more():
			dir = OLE.Directory.parse(stream.read(OLE.Directory.STRUCT.size))
			if dir.type == OLE.Directory.Type.INVALID:
				continue
			ole.dirs.append(dir)

		minifat_stream = ole.sid(ole.meta.minifat_start)
		minifat_count = (ole.meta.minifat_count * ole.meta.sect_size) // ole.meta.minisect_size
		for i in range(minifat_count):
			ole.minifat.extend(OLE.MiniFAT.parse(minifat_stream.read(ole.meta.minisect_size)))
		del minifat_stream

		root = ole.dirs[0]
		ole.ministream = ole.sid(root.start)

		for this in ole.dirs:
			if this.left_sid != 0xFFFFFFFF:
				this.left = ole.dirs[this.left_sid]
			if this.right_sid != 0xFFFFFFFF:
				this.right = ole.dirs[this.right_sid]
			if this.child_sid != 0xFFFFFFFF:
				this.child = ole.dirs[this.child_sid]

		return ole
