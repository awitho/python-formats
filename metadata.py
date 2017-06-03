
# coding=utf-8

import traceback

from pathlib import Path

from lxml import etree

from png import PNG, ParseError, CRCError


def main():
	import argparse
	parser = argparse.ArgumentParser()
	parser.add_argument("file")
	args = parser.parse_args()

	root = Path(args.file).resolve()
	if not root.is_dir():
		raise Exception("NOT A DIR")

	PNG.VERIFY = True

	decodables = ["zTXt", "tEXt", "iTXt"]
	ignorables = ["IDAT", "IHDR", "IEND"]

	for file in root.glob("**/*.png"):
		# print(file)
		try:
			png = PNG(file)
			chunks = png.chunks()
			while True:
				try:
					chunk = next(chunks)
				except StopIteration:
					break
				if chunk.cname == "exIf" or chunk.cname == "eXIf" or chunk.cname == "zxIf" or chunk.cname == "zXIf":
					print(file)
				# if chunk.cname in decodables:
				# 	decoded = chunk.decode()
				# 	if decoded.key == "XML:com.adobe.xmp":
				# 		xmp = etree.fromstring(decoded.text)
		except AttributeError:
			continue
		except ParseError as e:
			print("Failed on {}: {}".format(file, e.args[0]))
			continue
		finally:
			png.close()

if __name__ == '__main__':
	main()
