
# coding=utf-8

import mmap
import sys
import os
import zlib

from .common import Region

REGION_MAPPING = {
	"1": Region.USA,
	"A": Region.AMERICAS, # ?
	"C": Region.CHINA,
	"D": Region.GERMANY,
	"E": Region.USA,
	"F": Region.FRANCE,
	"H": Region.NETHERLANDS,
	"I": Region.ITALY,
	"J": Region.JAPAN,
	"K": Region.KOREA, # ?
	"O": Region.WORLDWIDE,
	"P": Region.EUROPE,
	"S": Region.SPAIN,
	"U": Region.ARGENTINA, # ?
	"X": Region.EUROPE, # multilanguage variant?
	"Y": Region.EUROPE, # multilanguage variant?
}

FORM_NAMES = {}
with open("gba.names", "rb") as f:
	while True:
		l = f.readline().decode("utf-8").strip("\r\n")
		if l.strip() == "":
			break
		if l.strip().startswith("#"):
			continue

		t = l.split("\t")
		if t[0] in FORM_NAMES:
			print("WARNING: Conflicting mapping for form \"{}\" -> \"{}\"".format(t[0], FORM_NAMES[t[0]]))
		FORM_NAMES[t[0]] = t[1]

PRETTIFY = {
	"°": "",
	":": "",
	"/": " "
}

def dict_replace(s, t):
	for needle, replacement in t.items():
		s = s.replace(needle, replacement)
	return s

def power_of_two(i):
	return (i != 0) and ((i & i - 1) == 0)


class GBA(object):
	def __init__(self, path, b):
		# raw values
		self.entrypoint = b[0x00:0x00 + 4 ]
		self.name =       b[0xA0:0xA0 + 12]
		self.id =         b[0xAC:0xAC + 6 ]
		self.unit =       b[0xB3:0xB3 + 1 ]
		self.device =     b[0xB4:0xB4 + 1 ]
		self.revision =   b[0xBC:0xBC + 1 ]

		# decoding
		self.entrypoint = int.from_bytes(self.entrypoint, "little")
		self.name = dict_replace(self.name.strip(b"\x00").decode("ascii"), PRETTIFY)
		self.id = self.id.decode("ascii")
		self.unit = int.from_bytes(self.unit, "little")
		self.device = int.from_bytes(self.device, "little")
		self.revision = int.from_bytes(self.revision, "little")

		# lookup
		try:
			self.pretty = dict_replace(FORM_NAMES[self.id], PRETTIFY)
		except KeyError:
			self.pretty = None

		try:
			self.region = REGION_MAPPING[self.id[3]]
		except KeyError:
			self.region = None

		# calculations
		self.crc = "{:x}".format(zlib.crc32(b))

		if self.revision == 0:
			self.revision = ""
		else:
			self.revision = " (r{})".format(self.revision)

		if power_of_two(os.stat(path).st_size):
			# todo: not this
			self.trimmed = ""
		else:
			self.trimmed = " (tr)"


def main():
	import argparse
	parser = argparse.ArgumentParser()
	parser.add_argument("dir")
	args = parser.parse_args()

	for path in os.listdir(args.dir):
		path = os.path.sep.join((args.dir, path))

		if not path.endswith(".gba"):
			continue

		rom = None
		with open(path, "rb") as f:
			with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as m:
				rom = GBA(path, m)

		if rom.pretty is not None:
			name = "{pretty} ({region_short}){revision} ({crc}){trimmed}.gba".format(region_short=rom.region.short_name(), **rom.__dict__)
		else:
			filename = os.path.basename(path)
			name = "{id}\t{filename}".format(filename=filename, **rom.__dict__)

		print(name)
		#os.rename(path, os.path.sep.join((args.dir, name)))

if __name__ == "__main__":
	sys.exit(main())
