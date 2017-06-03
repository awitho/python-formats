
# coding=utf-8

import traceback

from pathlib import Path
from enum import Enum
from pprint import pprint

from lxml import etree

from png import PNG, ParseError, CRCError
from jfif import JFIF

PNG.VERIFY = True


class FileType(Enum):
	UNKNOWN = 0
	PNG = 1
	JFIF = 2


def handle_png(file):
	decodables = ["zTXt", "tEXt", "iTXt", "exIf", "eXIf", "zxIf", "zXIf"]
	ignorables = ["IDAT", "IHDR", "IEND"]

	ret_chunks = []

	try:
		png = PNG(file)
		chunks = png.chunks()
		while True:
			try:
				chunk = next(chunks)
			except StopIteration:
				break
			if chunk.cname in decodables:
				decoded = chunk.decode()
				ret_chunks.append(decoded)
				if decoded.key == "XML:com.adobe.xmp":
					xmp = etree.fromstring(decoded.text)
			else:
				ret_chunks.append(chunk)
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

def main():
	import argparse
	parser = argparse.ArgumentParser()
	parser.add_argument("file")
	args = parser.parse_args()

	root = Path(args.file).resolve()
	if not root.is_dir():
		raise Exception("NOT A DIR")

	handlers = {
		FileType.PNG: handle_png,
		FileType.JFIF: handle_jfif,
	}

	for file in root.glob("**/*"):
		filetype = guess_type_from_filename(file)
		if filetype == FileType.UNKNOWN:
			continue
		meta = handlers[filetype](file)
		print("# {}".format(file))
		if meta is not None:
			pprint(meta)

if __name__ == '__main__':
	main()
