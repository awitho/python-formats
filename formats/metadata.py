
# coding=utf-8

import sys
import traceback

from enum import Enum
from pathlib import Path
from pprint import pprint

from lxml import etree

from jfif import JFIF
from exif import IFDTagType
from png import PNG, ParseError, CRCError, Chunks

PNG.VERIFY = True

EXIF_TAGS_TO_NAMESPACE = {
	# IFD0
	IFDTagType.DateTime: "exif date",
	IFDTagType.ImageDescription: "exif description",
	IFDTagType.Make: "exif make",
	IFDTagType.Model: "exif model",
	IFDTagType.Software: "exif software",
	IFDTagType.Artist: "exif artist",
	IFDTagType.Copyright: "exif copyright",
	# ExifIFD
	IFDTagType.MakerNote: "exif maker note",
	IFDTagType.UserComment: "exif comment",
	IFDTagType.DateTimeOriginal: "exif date taken",
	IFDTagType.DateTimeDigitized: "exif date digitized",
	IFDTagType.CameraOwnerName: "exif owner name",
}

class FileType(Enum):
	UNKNOWN = 0
	PNG = 1
	JFIF = 2


def handle_png(file):
	text = ["zTXt", "tEXt", "iTXt"]

	ret_chunks = []

	try:
		png = PNG(file)
		chunks = png.chunks()
		while True:
			try:
				chunk = next(chunks)
			except StopIteration:
				break

			try:
				decoded = chunk.decode()
			except:
				print("Skipping {} chunk due to\n{}".format(chunk.cname, traceback.format_exc()))
				continue

			if decoded:
				if chunk.cname in text and decoded.key == "XML:com.adobe.xmp":
					ret_chunks.append(etree.fromstring(decoded.text))
				else:
					ret_chunks.append(decoded)
	except ParseError as e:
		print("Failed on {}: {}".format(file, e.args[0]))
		return
	finally:
		png.close()

	return ret_chunks

def handle_jfif(file):
	return JFIF.from_file(str(file))

def guess_type_from_filename(file):
	if file.suffix == ".png":
		return FileType.PNG
	elif file.suffix == ".jpg":
		return FileType.JFIF

	return FileType.UNKNOWN

handlers = {
	FileType.PNG: handle_png,
	FileType.JFIF: handle_jfif,
}

def handle_file(file):
	filetype = guess_type_from_filename(file)
	if filetype == FileType.UNKNOWN:
		return False
	print("# {}".format(file))
	meta = handlers[filetype](file)
	if meta is not None:
		pprint(meta)
	return True

def main():
	import argparse
	parser = argparse.ArgumentParser()
	parser.add_argument("file")
	args = parser.parse_args()

	root = Path(args.file).resolve()
	if not root.is_dir() and root.is_file():
		handle_file(root)
	elif not root.exists():
		raise Exception("u wot m8")

	for file in root.glob("**/*"):
		if not handle_file(file):
			continue

if __name__ == '__main__':
	main()
