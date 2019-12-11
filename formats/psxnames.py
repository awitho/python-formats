#!/usr/bin/env python

import mmap
import os
import re
import sys

from pprint import pprint
BOOT_MATCH = re.compile(rb"BOOT ?= ?cdrom:\\(.*)", re.MULTILINE)

for (a, b, files) in os.walk("."):
	for name in files:
		if not name.lower().endswith(".bin"):
			continue

		meta = {}
		with open(a + os.path.sep + name, "rb") as f:
			s = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
			match = BOOT_MATCH.search(s)
			if match == None:
				print("Failed to find boot strip in {}".format(name))
				continue

			meta['id'] = match.group(1).decode("ascii").rstrip("\r").rstrip("\t").rstrip("1").rstrip(";").upper()
			# f.seek(0x9319)
			# meta['cdn'] = f.read(0x5).decode("ascii").strip(" ")
			f.seek(0x9320)
			meta['vendor'] = f.read(0x20).decode("ascii").strip(" ")
			f.seek(0x9340)
			meta['name'] = f.read(0x20).decode("ascii").strip(" ")
			# meta['file'] = name
			print(name)
			pprint(meta)
