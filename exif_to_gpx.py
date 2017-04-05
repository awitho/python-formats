
# coding=utf-8

import traceback
import sys

from datetime import date

from enum import Enum
from pathlib import Path

import exifread
from exifread.utils import Ratio
from exifread.tags import exif


class Direction(Enum):
	N = 0
	S = 1
	W = 2
	E = 3


class GeographicCoordinate:
	def __init__(self, degrees=0, arcminutes=0, arcseconds=0, direction=Direction.N):
		self.degrees = float(degrees)
		self.arcminutes = float(arcminutes)
		self.arcseconds = float(arcseconds)
		self.direction = direction

	def is_valid(self):
		return not (self.degrees == 0 and self.arcminutes == 0 and self.arcseconds == 0 and self.direction == Direction.N)

	def to_decimal(self):
		dec = self.degrees + (self.arcminutes / 60) + (self.arcseconds / 3600)
		if self.direction == Direction.S or self.direction == Direction.W:
			dec = -dec
		return dec

	def __str__(self):
		return "{}° {}' {}'' {}".format(self.degrees, self.arcminutes, self.arcseconds, self.direction.name)


class Position:
	def __init__(self, lng, lat, altitude=0):
		self.lng = lng
		self.lat = lat
		self.altitude = altitude

	def is_valid(self):
		return self.lng.is_valid() and self.lat.is_valid()

	def __str__(self):
		return "{} {} @ {}'".format(self.lat, self.lng, self.altitude)


class Waypoint:
	def __init__(self, pos=None, moment=None, name="Unnamed"):
		self.pos = pos
		self.moment = moment
		self.name = name

	def is_valid(self):
		return self.pos.is_valid()

	def __str__(self):
		return "{} @ {}".format(self.pos, self.moment)

	def __repr__(self):
		return str(self)

	def to_wpt(self):
		return """<wpt lat="{}" lon="{}">
	<name>{}</name>
	<ele>{}</ele>
	<time>{}</time>
</wpt>""".format(self.pos.lat.to_decimal(), self.pos.lng.to_decimal(), self.name, self.pos.altitude, self.moment.isoformat())

"""
GPS GPSImgDirection [25893/431]
GPS GPSDate 2015:12:27
GPS GPSAltitudeRef [0]
GPS GPSSpeedRef K
GPS GPSDestBearing [25893/431]
GPS GPSImgDirectionRef T
GPS Tag 0x001F [10]
GPS GPSDestBearingRef T
GPS GPSSpeed [0]
GPS GPSTimeStamp [5, 35, 28]
"""


def parse_waypoint(file):
	with file.open("rb") as f:
		data = exifread.process_file(f, details=False)
		waypoint = Waypoint(Position(GeographicCoordinate(0, 0, 0), GeographicCoordinate(0, 0, 0)), date(1, 1, 1))
		for (key, value) in data.items():
			if not key.startswith("GPS"):
				continue
			name = key[4:]
			for (i, val) in enumerate(value.values):
				if isinstance(val, Ratio):
					if val.den != 0:
						value.values[i] = val.num / val.den
					else:
						value.values[i] = val.num

			if name == "GPSLongitude":
				waypoint.pos.lng = GeographicCoordinate(*value.values, direction=waypoint.pos.lng.direction)
			elif name == "GPSLatitude":
				waypoint.pos.lat = GeographicCoordinate(*value.values, direction=waypoint.pos.lat.direction)
			elif name == "GPSLatitudeRef":
				try:
					waypoint.pos.lat.direction = Direction[value.values]
				except KeyError:
					pass
			elif name == "GPSLongitudeRef":
				try:
					waypoint.pos.lng.direction = Direction[value.values]
				except KeyError:
					pass
			elif name == "GPSAltitude":
				waypoint.pos.altitude = value.values[0]
			elif name == "GPSDate":
				waypoint.moment = date(*[int(i) for i in value.values.split(":")])
		return waypoint


def main():
	import argparse
	parser = argparse.ArgumentParser()
	parser.add_argument("file")
	args = parser.parse_args()

	root = Path(args.file).resolve()
	if not root.is_dir():
		raise Exception("NOT A DIR")

	coords_file = Path(root.name + ".gpx")
	with coords_file.open("w") as f:
		f.write("<gpx>\n")
		count = 1
		for file in root.glob("**/*"):
			if not (file.suffix == ".jpg" or file.suffix == ".jpeg"):
				continue

			sys.stdout.write("\r{}".format(count))
			sys.stdout.flush()
			try:
				waypoint = parse_waypoint(file)
				if waypoint.is_valid():
					waypoint.name = str(file.relative_to(root))
					print("\r" + waypoint.name)
					f.write(waypoint.to_wpt())
					f.write("\n")
					f.flush()
			except Exception:
				print("Failed to process file {} due to:\n{}".format(str(file), traceback.format_exc()))
			count += 1

		f.write("</gpx>\n")

if __name__ == '__main__':
	main()
