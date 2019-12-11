
# coding=utf-8

import os
import binascii
import io
import traceback

from enum import Enum


def byteswap(b):
	i = iter(b)
	for x, y in zip(i, i):
		yield y
		yield x

FORM_NAMES = {}
with open("n64_official.names", "rb") as f:
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


class UnknownCountryCode(Exception):
	pass

class InvalidCartridgeFormat(Exception):
	pass

class Cartridge(io.FileIO):
	MAGIC = b"\x80\x37\x12\x40"
	BYTESWAPPED_MAGIC = bytes(byteswap(MAGIC))

	class Country(Enum):
		Unknown = 0xFF
		Germany = 0x44
		USA = 0x45
		France = 0x46
		Japan = 0x4A
		Europe = 0x50
		Australia = 0x55
		Australia_Fake = 0x58

		def code(self):
			if self == Cartridge.Country.Germany:
				return "DE"
			elif self == Cartridge.Country.USA:
				return "US"
			elif self == Cartridge.Country.France:
				return "FR"
			elif self == Cartridge.Country.Japan:
				return "JP"
			elif self == Cartridge.Country.Europe:
				return "EU"
			elif self == Cartridge.Country.Australia or self == Cartridge.Country.Australia_Fake:
				return "AU"
			elif self == Cartridge.Country.Unknown:
				return "??"

	class Endian(Enum):
		BIG = 0xFFFE
		LITTLE = 0xFEFF
		BYTESWAPPED = 0xFEFE

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

		self.byteswapped = False

		self.header = self.read(4)

		self.byteswapped = self.is_big_endian_byteswapped(self.header)

		if not (self.is_big_endian(self.header) or self.byteswapped):
			raise InvalidCartridgeFormat()

		self.lat = self.header[0:1]
		self.pgs = self.header[1:2]
		self.pwd = self.header[2:3]
		self.pgs = self.header[3:4]

		self.clockrate = self.read(4)
		self.pc = self.read(4)
		tmp = self.read(4)
		self.unknown = tmp[:3]
		self.release = tmp[3:].decode("ascii")
		self.crc1 = binascii.hexlify(self.read(4)).decode('ascii')
		self.crc2 = binascii.hexlify(self.read(4)).decode('ascii')

		self.skip(8)

		self.name = self.read(20)

		self.skip(4)

		self.manufacturer = self.read(4).lstrip(b"\x00").decode("ascii")
		self.id = self.read(2).decode('ascii')
		self.country, self.revision = list(self.read(2))
		try:
			self.country = Cartridge.Country(self.country)
		except ValueError:
			print(self.country)
			self.country = Cartridge.Country.Unknown

		self.name = self.decode_name().strip(" ")

	def decode_name(self):
		if self.country == Cartridge.Country.Japan:
			return self.name.decode("Shift-JIS")
		else:
			return self.name.decode("ascii")

	def form(self):
		return "{}{}-{}_{}".format(self.manufacturer, self.id, self.country.code(), self.revision)

	def extension(self):
		if self.byteswapped:
			return ".v64"
		else:
			return ".z64"

	def format_dictionary(self):
		try:
			form_name = FORM_NAMES[self.form()]
		except KeyError:
			form_name = "\x00!!! UNKNOWN GAME"

		return {
			"cc": self.country.code(),
			"crc1": self.crc1,
			"crc2": self.crc2,
			"country": self.country.name,
			"ext": self.extension(),
			"form": self.form(),
			"form_pretty": form_name,
			"id": self.id,
			"manufacturer": self.manufacturer,
			"name": self.name,
			"release": self.release,
			"revision": self.revision,
			"unknown": self.unknown
		}

	def skip(self, i):
		self.seek(i, io.SEEK_CUR)

	def read(self, size=None):
		# TODO: fix this for odd number reads and positions
		buf = super().read(size)
		if not self.byteswapped:
			return buf
		else:
			return bytes(byteswap(buf))

	def is_big_endian(self, header):
		return header == Cartridge.MAGIC

	def is_big_endian_byteswapped(self, header):
		return header == Cartridge.BYTESWAPPED_MAGIC

	def __repr__(self):
		return "{} ({})".format(self.name, self.country.code())

PRETTIFY = {
	"°": "",
	":": "",
	"/": " "
}

def dict_replace(s, t):
	for needle, replacement in t.items():
		s = s.replace(needle, replacement)
	return s

def main():
	from pprint import pprint
	import argparse

	parser = argparse.ArgumentParser()

	parser.add_argument("file")
	subparsers = parser.add_subparsers(dest="verb")

	info_parser = subparsers.add_parser("info")
	info_parser.add_argument("--format", default="{crc1: <8} {crc2: <8} {id} {cc} {revision: >8} {manufacturer: >12} {release: >7} {name: >20} {form_pretty} {filename}")
	info_parser.add_argument("--sort", default="{cc}{form_pretty}")
	info_parser.add_argument("--append-revision", dest="use_revision", action="store_true")

	rename_parser = subparsers.add_parser("rename")
	rename_parser.add_argument("--format", default="{form_pretty} ({cc}) ({crc1})")
	rename_parser.add_argument("--sort", dest="sort", default="", help="This option does nothing when renaming.")
	rename_parser.add_argument("--append-revision", dest="use_revision", action="store_true", default=True)

	deduplicate_parser = subparsers.add_parser("deduplicate")
	deduplicate_parser.add_argument("--delete", action="store_true")

	convert_parser = subparsers.add_parser("convert")
	convert_parser.add_argument("--output", "-o", dest="out")

	dedump_parser = subparsers.add_parser("dedump")

	args = parser.parse_args()

	if not os.path.isdir(args.file):
		return

	names = {}

	for (path, dirs, files) in os.walk(args.file):
		for file in files:
			try:
				with Cartridge(path + os.sep + file, "rb") as f:
					names[(path, file)] = f
			except Exception as e:
				print(file)
				traceback.print_exc()
				continue

	if args.verb == "rename" or args.verb == "info":
		if args.verb == "info":
			print(args.format.format(**{
				"name": "Name",
				"cc": "CC",
				"crc1": "CRC",
				"crc2": "CRC",
				"country": "Country",
				"id": "ID",
				"manufacturer": "Manufacturer",
				"release": "Release",
				"revision": "Revision",
				"form": "Form",
				"form_pretty": "Real Name",
				"filename": "Filename"
			}))

		for (key, cart) in sorted(names.items(), key=lambda x: args.sort.format(**x[1].format_dictionary())):
			try:
				filename = args.format.format(filename=key[1], **cart.format_dictionary())
				# TODO: remove this hacky check for master quest
				if args.use_revision and cart.revision > 0 and not (cart.id == "ZL" and cart.revision == 15):
					filename += " (r{})".format(cart.revision)
				if args.verb == "info":
					print(filename)
					print()
				else:
					filename += cart.extension()
					filename = dict_replace(filename, PRETTIFY)
					os.rename(os.sep.join(key), key[0] + os.sep + filename)
			except KeyError:
				print(key)
				traceback.print_exc()
				continue
	elif args.verb == "dedump":
		for (key, cart) in names.items():
			print("{}\t{}".format(cart.form(), FORM_NAMES[cart.form()]))
	elif args.verb == "deduplicate":
		dups = []
		identifiers = {}

		for key in names.keys():
			cart = names[key]
			form = cart.form()

			if form not in identifiers:
				identifiers[form] = []

			category = identifiers[form]
			category.append(key[1])

			if len(category) > 1 and cart.form() not in dups:
				dups.append(cart.form())

		for dup in dups:
			print("{}: {}".format(dup, identifiers[dup]))
	elif args.verb == "convert":
		_, cart = next(iter(names.items()))

		cart.seek(0)
		with open(args.out, "wb") as f:
			f.write(cart.read())

if __name__ == '__main__':
	main()
