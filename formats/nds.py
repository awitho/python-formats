
# coding=utf-8

import mmap
import sys
import os
import zlib

from .common import Region

REGION_MAPPING = {
	"E": Region.USA,
	"J": Region.JAPAN,
	"O": Region.WORLDWIDE,
}

FORM_NAMES = {}
with open("nds.names", "rb") as f:
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


class NDS(object):
	def __init__(self, path, b):
		self.name = dict_replace(b[0:12].strip(b"\x00").decode("ascii"), PRETTIFY)
		self.id = b[12:18].decode("ascii")

		self.pretty = dict_replace(FORM_NAMES[self.id], PRETTIFY)
		self.region = REGION_MAPPING[self.id[3]]
		self.crc = "{:x}".format(zlib.crc32(b))
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

		if not path.endswith(".nds"):
			continue

		rom = None
		with open(path, "rb") as f:
			with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as m:
				rom = NDS(path, m)

		name = "{pretty} ({region_short}) ({crc}){trimmed}.nds".format(region_short=rom.region.short_name(), **rom.__dict__)

		os.rename(path, os.path.sep.join((args.dir, name)))

if __name__ == "__main__":
	sys.exit(main())
