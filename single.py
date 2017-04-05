
# coding=utf-8

from pathlib import Path

from lxml import etree

from png import PNG, ParseError, CRCError


def main():
	import argparse
	parser = argparse.ArgumentParser()
	parser.add_argument("file")
	args = parser.parse_args()

	file = Path(args.file).resolve()
	if not file.is_file():
		raise Exception("NOT A DIRFILE")

	PNG.VERIFY = True

	doitfaggot = ["meTa", "cmOD", "cpIp"]
	try:
		png = PNG(file)
		chunks = png.chunks()
		while True:
			try:
				chunk = next(chunks)
			except StopIteration:
				break
			#if chunk.cname in decodables:
			#	decoded = chunk.decode()
			#	print(chunk.cname, decoded.key)
			#	if decoded.key == "XML:com.adobe.xmp":
			#		xmp = etree.fromstring(decoded.text)
			if chunk.cname in doitfaggot and chunk.length > 0:
				with open(file.name + "." + chunk.cname, "wb") as f:
					f.write(chunk.data)
	except AttributeError:
		pass
	except ParseError as e:
		print("Failed on {}: {}".format(file, e.args[0]))
	finally:
		png.close()

if __name__ == '__main__':
	main()
