
# coding=utf-8

import traceback

from pathlib import Path

from ole import OLE

VALID_ASCII = range(32, 126 + 1)


def replace_noascii(s):
	buf = ""
	for c in s:
		if ord(c) not in VALID_ASCII:
			buf += "_"
		else:
			buf += c
	return buf


def traverse(rootnode):
	thislevel = [rootnode]
	a = '                                 '
	while thislevel:
		nextlevel = list()
		a = a[:len(a) - 2]
		print(a, end='')
		for n in thislevel:
			print(str(n.name) + " ", end='')
			# if n.left:
			# 	nextlevel.append(n.left)
			# if n.right:
			# 	nextlevel.append(n.right)
			if n.child:
				nextlevel.append(n.child)
			thislevel = nextlevel
		print()


def main():
	import argparse
	parser = argparse.ArgumentParser()
	parser.add_argument("file")
	args = parser.parse_args()

	file = Path(args.file).resolve()
	if not file.is_file():
		raise Exception("NOT A DIRFILE")

	with OLE.fromfile(str(file)) as ole:
		for directory in ole.dirs:
			if directory.type != OLE.Directory.Type.STREAM:
				print("'%s' isn't a stream it's a %s." % (directory.name, directory.type))
				continue

			try:
				if directory.size < ole.meta.minisect_size:
					stream = ole.minisid(directory.start)
				else:
					stream = ole.sid(directory.start)
			except Exception:
				print("Failed to grab stream for '%s' due to:\n%s" % (directory.name, traceback.format_exc()))
				continue

			try:
				with open(replace_noascii(directory.name) + ".bin", "wb") as f:
					while stream.has_more():
						f.write(stream.read())
			except Exception:
				print("Failed to write '%s' due to:\n%s" % (directory.name, traceback.format_exc()))
				continue
			print("'%s' wrote." % directory.name)


if __name__ == '__main__':
	main()
