
# coding=utf-8

import sys
import traceback

from enum import Enum
from pathlib import Path
from pprint import pprint

from lxml import etree

from jfif import JFIF
from png import PNG, ParseError, CRCError

PNG.VERIFY = True


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
			decoded = chunk.decode()
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
	meta = handlers[filetype](file)
	print("# {}".format(file))
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
