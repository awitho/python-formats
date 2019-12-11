
# coding=utf-8

import argparse
import struct
import io
import os
import json
import traceback
import zlib
import sys


class Bunch(dict):
	def __getattr__(self, attr):
		return self[attr]

	def __setattr__(self, attr, value):
		self[attr] = value


class HFSException(Exception):
	pass


class NoCentralDirectoryEndException(HFSException):
	pass


class NoCentralDirectoryException(HFSException):
	pass


class NoLocalFileException(HFSException):
	pass


class HFS(io.FileIO):
	LOCAL_FILE_HEADER = b"HF\x01\x02"
	CENTRAL_DIRECTORY_HEADER = b"HF\x01\x02"
	CENTRAL_DIRECTORY_END_HEADER = b"HF\x05\x06"
	CENTRAL_DIRECTORY_END_SIZE = 18

	CHECKSUM_KEY = bytearray.fromhex('9eb802280888055fb2d90cc624e90bb1877c6f2f114c6858ab1d61c13d2d66b653aebca9c59ebbde7fcfb247e9ffb5301cf2bdbd8ac2baca3093b353a6a3b4240536d0ba9306d7cd2957de54bf67d9239041dc760671db01bc20d2982a10d5ef8985b1711fb5b606a5e4bf9f33d4b8e8a2c9077834f9000f8ea8099618980ee1bb0d6a7f2d3d6d08976c6491015c63e6f4516b6b62616c1cd83065854e0062f22083b8edb6b3bf9a0ce2b6039ad2b1743947d5eaaf77d29d1526db048316dc73120b63e3843b64943e6a6d0da85a6a7a5861b24dce51b53a7400bca3e230bbd47dd4da1aebe4dd6d51b5d4f4c785d383a7ffd7c231cfd0b58b9ed92c1daede5bb0c2649b26f263ec9ca36a750a936d02a906099c3f360eeb8567077213570005824abf95147ab8e2ae2bb17b381bb60c9b8ed2920dbed5e5b7efdc7c21dfdb0bd4d2d38642e2d4f1f8b3dd686e83da1f3c710550aa41022710100bbe86200cc925b56857b3856f2009d466b99fe461ce0ef9de5e98c9d9292298d0b0b4a8d7c7173db359810db42e3b5cbdb7ad6cbac056986c13c0a86b647af962fdecc9658a0bcf0ee49dff099327ae000ab19e077d44930ff0d2a3088768f2011efec206695d5762f7cb67658071366c19e7066b6e761bd4fee02bd3895a7ada10cc4add674f5c0114d96c0663633d0ffaf50d088dc8206e3b5e10694ce44160d5727167a2ed95066c7ba5011bc1f4088257c40ff5c6d9b06550e9b712eab8be8b7c88b9fcdf1ddd62492dda15f37cd38c654cd4fb00000000963007772c610eeeba51099995770ccc03470bbbb91602222f260555be3bbac5280bbdb2925ab42b046ab35cd1e4033c47d4044bfd850dd26bb50aa537be0bb4a18e0cc31bdf055a8def022dfaa8b5356c98b242d6c9bbdb40f9bcace36cd832755cdf45cf0dd6dc593dd1abac30d9263a00de518051d7c81661d0bfb5f4b42123c4b3569995bacf0fa5bdb841a5df4ad795d83d6dc4d1a4fbf4d6d36ae96943fcd96e34468867add0b860da6fdfb9f9f9efbe8e43beb717d58eb060e8a3d6d67e93d1a1c4c2d83852f2df4ff167bbd16757bca6dd06b53f4b36b248da2b0dd84c1b0aaff64a0336607a044119c46d078ff46a7035a563e9a395649e3288db0ea4b8dc791ee9d5e088d9d2972b4cb609bd7cb17e072db8e7911dbf906410b71df220b06a4871b9f3de41be84732d0444e51d03335f4c0aaac97c0dddc3ef60df55df67a8ef8e6e3179be69468cb361cb1a8366bca0d26f2536e26852cd16be815b26b9f6e177b06f7747b718e65a0888706a0fffca3b06665c0b0111ff9e658f69ae62f8d3ff6b6145cf6c1678e20aa0eed20dd75483044ec2b30339612667a7f71660d04d476949db776e3e4a6ad1aedc5ad6d9660bdf40f03bd8372e7a66b3b84a61c4021b685d942b6f2a')
	CHECKSUM_KEY_LEN = 1024
	XOR_KEY = bytearray.fromhex('78bd02478cc9165390d52a6ea5e03f7aa9ec5396dd184481c20778bdf60c4b86fd034489ca17509dd64287c80c5792dd186baee1247fbaf24f94bafd2063aee9549fd50a4f84c13e7b88cd12579dd867a2e10d5097da19418fca195c93d62d68a7e22167a8ed5693dc194a8fc0057fbaf5305396fc01428fc8145fbbfe4184cf0a5590d3296ea3e03d7ab7ec5196db19446eab185d92d70c4986c201448bce15509fda6985cb0c5192df1865aee31b5e96d32c69baff2065aeeb5490d316498cc7027db8cb0e569bd865a28cc73376b9fc408dca175c91d62b68a5e23e65a8ef5291dc1b468dc0045e95d00f4ab9fc03468dcb145192fe4384c90a5790dc176aade0237eb9d13277b9fc2762ade85b9ed1144f85c23f4489ce13509dda67adc90c537bb805428fc4195f92d12c6ba6fd2067aae95790dd164b8cc1027fb8f53277b8fd06438cc91a76bbfd4083ce09549fd21568abe13e7ba8ed5297bffa2560a4195e93d00d4a87fc01468ac914539ed54184cb0e5593dc194d80c71a5994d32e76bbfc2162afe8559ed314488bc6017c87ca0d5093fb054083ef3275b8fb4681cc185d92d72c69a6e32065aaee5590df1a4961a61b5895d30e75b8ff02418ccb165dbaff4085ce0b5491d21768ace71f5895ce3374b9fa2761ace75a9dd0134e89c43f458acf14519edb6884aaed377cb9064380c51a5f94d12f6ab9fc2366ade85792d117488dc6035b96ed3077bafa07408dc63277b8fd4683cd085b9ed1146faae52063a9cd3073bef9246fa2e55894d10e4bb8fd02478cc9165291fd4087ca09547ebb084c83c61d5897d23174bbfe2663ace95a9fd0154e8bc4004386c93172bff8054eaaee3174bffa4580c306599cd02d6aa7fc2166abe85592bbe82d62a71c5996d33075bbfe05408fca1975b8ff4282cf08559ed3144e85c01f598acf3075befb2461a2e7599cd7124d88fb3e4184cf15529ff72366a9ec3772bd074c81c61b5895d22f74b9ff2261aceb569dd0174a64a01f5aa9ec3376bdf8074282ee3374b9fa4780cd065b9dd0136ea9e4024788cd3672bdf82b6ea1e45f9ad51074b9fe03408dca175cb8fd4386a8f5327fb4094e83c01c5b96cd3077baf92463aee65b9cd1124f88c53e64abed3673bcf90a66abec3172bef9448fc205589bd6116cb8fd2267acca3570b3f62963a01d5a97ec3176bbf805438ec53174bbfe4580cf0a5a70b70a4984c31e4588cf3172bff8256ea3e4599ad7114cb7fa3d4083ce3471b2df2265a8eb3671bcf74a8dc71c5996d33075baff2461afea599cb6eb2865a21f64a8ef3271bcfb064da9ec3375befb4481c207589dd6134885de034489ca3770bdf62a6da0e35e99d42f72b5f804418ecb1874b9dd2063aef63370b50a4f84c11e5b88cc3376bdf82762a1e45b9ed6134c669d2067aae93473bdf62267a8ed3673bcf94a8ec1045f9ad51073b6f901438ec9347fb2f5286ba6e15ba8ed3277bcf9064380ec3077baf94483abf83d72b70d4887c201448bce3570bff92a6fa0e55e9bd41172b7f93c62afe8357e9adf2065afea3570b3f6498cc7025d97cc3176bbf82562afc73a72b7ec2966a32065aaef3470bffa0965a8ef3271bcfb458ec3045975b00f4a99dc00458ecb3471b2f7286da6e25d98eb2e71b4ff3a4580c4135699dc2762ade83b7eb60b4885c21f4489ce3370bcfb266da0e75a99b1ee2b599c2366ade83772b1dd2064a9ea3770bdf64b8cc1025e99d40f5798dd06438cc93b7eb1f42f6aa5e063a6e93370bdfa074ca8ed3277bce5226fa4f93e73b00d4a87dd00478ac93473bef5286fa1e25f98d52e735b9e2560ace93a569bdc2162afe8357fb2f5488bc6015c87ca0d77bcf9054083c6397cb7f22a679c2166abe83572bff42164abee3570bffa498ca6fa3974b30e5598df02418cc8357eb3f4296aa7e05da6ea2d70b3fe3961a2ce135498db2661ace73a7db0f34e86c300458acf3471befb286ca3fb3875b2ef14599e2361aceb367d99dc2366ade83471b2f7488dc6035c76ad135499da07408dc63b7cb1f32e69a4df62a5e82b76b1fb0864a9ee10539ed9246fa5fa3f74b10e4b98dd02478dc83772b1f42b6ea5e05f998dd0175a992463aee5115798dd2663ace93a7fb0f54f8ac5004386c90c529fd8044f82c5387bb6f12c579a2267ace93673b0dc2166abe93473bee82d62a7fc3976b211549bde05408fca397cb0f52e6ba4e162a7e82d765f98256e8acf10559edb2460a3e6397cb7f24d88db1e468bc83572bff40a4d80c33976b3d0155a9f2461aeeb395598df2261aceb367db0f4498aa0ff3a69ac13569ddb044182c7387db6f32c699bde61a4ef2a75b0f31f4789cc17529dd82b6ea1e43f75b20f5499de03408dca377db0f72a69a4fe3b488dd2165d982762a1cd10579ad92760ade63b7cb1f24f88c51f4268ad16539cd90a4f80c43f7ab5f0135699dc67a2ea377c98dd2267ace9155094e92e63a0fd3a77ac11569ad904438ec5387fb2f12c68a5de63a48ed5105f9a29468bcc11529fd8256ea3e4387bb6f14c97da1d4083ce365093d6094c87c23d788bd1165b982562afe410559ade2560afea397cb3eb2865a3fe2568af12519cdb064d83c4397ab7f02d569bdc61a3ee297452be034489ca17519cd72a6da0e33e79b4ef559adf04418ecb387db2f7084582ff04498ed3105d9a266d89cc13569dd82762a1e7387db6f34c89bde0276aaa17509dd60b4c81c23f78b4cf125598db66a1ec275399de23438ec9145f92d52864a1fe3b68ad12579cd9064281c43b7eb5f02f6a99c1074a89d4135e9501448bce16539cd92a6fa0e53e7bb4f05396d91c476fa8155e93d5084b86c13c478acd1053992663a0cc11569bd82562aee51d5297ec2966a3e0256bae15509fda094c83c63d7bb4f1125798dd66a38bd61e7abf00458ecb145192d7296ca7e23d78abee5194df05428fc4395d90d30e4984c0054a8fd4115e9b284489cf12519cdb266da0e73a79b7ef2a79bce3266da8175292d7084d86c33c798acf10549fda65a0e30f5278bd06428dc81b5e91d42f6aa5e02469ae13509dda074c81c63a79b4f30b78bdc2074c89d71251bd00478ac914539ed62b6ca1e23f78b5ee5394bde6236ca91a5f90d50e4b85c0034689cc17529dd86b88cd12579cd9264083c6195390ed2a67bce1266ba815539ed5084f82c13c7bb6cd135499c5004f8ad93578bf01428fc8155e93d4296aa7e13c67aaed5093de194462a6195c97d20d48bbfe014488d5125f9400458acf14519fda296ca3e6185592ef3478bfe2216cab165d90d70a4a87c03d468bcc11529fd864afaef33479ba07408dc61a5d90d32e69a4ff2265a814519edb084d82c73c5a95cf3479bec3004d8ad71c78bc03468dc8175291d42b6ea6e33c79aaf0377ab9e4236da61b5c91d20f4885fe034588cb16519cd74386c90c507eb9044f82c5185b96d12b78bde2276ca9165390d50b4e85c03f7a89cc367bb8c4034e85f1347bbe05408fc91a5f90d52e6ba4e12267a9ec5792b8e52e63a4195a96d10c77bafd00438ec91450bc01468bc815529fd4294287dc195693f0357abfe4206faa195c93d60d4887c2024788cd16539cc60d69acf0357ebb044182c7185d96d22d68bbfe2164afea5590d4094e60a31e5994ef3275bfc4014e8bd83479be03408ccb165d90d72a69a4e31b498cf3367db8e72261a41b5d96d30c49baff00458ecb155093ff4285adf6337cb90b4e81c41f5a95d03376b9e3206daa175c91d60b4885c33e68adf2377cb9c60340adf0377ab904438ec5185f91d22f68a5fe2364a9f5307cb9ea2f60a51e5b94d13276b9fc07428dc81b77bafd478cc9165373b6094c87c21a578cf1367bb8e5226fa4185f92d10c4b86fd00478aca307fbac92568aff2317cb8054e83c4195a97d02d76bafd2063aee9549fb7e82d67a21d58abee3174bffa054f84f0357abf04418ecb185c93d62d4582df04498ef3317cbbe62d60a71a5994d30d76bbfc01428fc8155ebae32469aaf7307db60b4c81c31e5994cf3275b8fb2661ab185d92d70c4965a02366aef3307dbac70c68adf2377db8074281c41b5e95d02f69baff074a89f4337eb5e82c61a21f5895ee3374b9fa06418cc73376b9fc4782a8f43f72b5084b86c11c478af2377cb9e62360a51a5f94d00f4ab9fc036ba8f5327fb5e1246baef5307fba094c80c51e5b94d13277b8fd2662adf53e73b4e92a67a01d67aaed3073bef9044fabee367bb805428fc4195e70b3094683c0054a8ff4317ebbe92c63a61d5897d23174bbfd06438cc93d599ce3266dabf43172b7084d86c31c598bce3174bffa2560a3e65993b3ee29649f2265a8eb367ebbc82469aef3307dba074d80c71a5994d32e589dc2064d88f73271b4eb2e65a01c59aaef3075befb044182ef3275b8e6236ca9fa3f70b40f4a85c0034689cc3772bae72c61a61b5895d20f745de2276ca9f633709ce1266aa9f4337eb5084f82c11c5895ce3374b9fa004f8af93f70b5ee2b64a12267a8ed3772bdf80b67aaed3073be064380a6f93c77b20d489bc1064b88f5327fb4e92e63a11c5b96ed3077baf9046eaaf915589fe2216cabf63d73b4094a87c01d468bcc3173bef9246fa2f83d76b3ec285b9e2164afea3570b3df256aaff4317ebb084d82c71d5872cf14599ec3004d8af63d70b7ea2964a31e65a8ec3172bff8054eaaef175a9ae7206da6fb3c71b20f4884df024588cb3671bcf72a62a71c5996b0d316599c276daaf73c589de2276ca9f63271b40b4e85c01f5a89cc305a99c4034e85f83f72b1ef28659e2364a9ea3770bdf72366a9ec3772bde52e63a5f83b76b10c579add004389f63370b5ea2f64a11e5ba9ec337658e5226fa4d0155b9ee5206faaf93c73b60d4b84c1024788cd3673bcf90e4384f93a77b0ed165b9c2063aee9347f9bde2164aff5327fb4094e83a3fe3974d0155a9fc4014e8bf83d72b6ed2867a22164abee3570bcf90a498cd3165d98e72262a7f83d76b30c499adf00448fca3570b3f6296ca7ff39748fd215589b2661ace714599ee3206daaf73c71b60a4984c31e456dd2175c99c7024184fb3e75b0ef2a599f2065aeeb3471b2de2364a8eb135c99ea2f60a5fe3b75b0135699dc07428dc83b71b6eb2865a21f64a98dd01c59e623608cd1165b98e5236ea5f83f72b10c4b86dd034489ca375f9ac90c4386fe3b74b1d217589d2663ace83b579add2063aee9347fb5e92c67a2fd386bae115498c5024f84f93e73b0ed2a669d2067aae934735be804488fd2115c9be62d60a7fa3a77b00d569bdc01428fc8347fb2f50d4683fc394a8fd1145f9a2560a3cf125598e4216eabf83d72b70c4986bfe4296ed3105d9ac70c4187fa3974b3ee15589f2261afe8357e9adf204a89d4135d96eb2c61a2ff3875ae135598db06418cc73a7db0f32966a3c306498cd7125d982c488dd2175c99e62360a5fb3e75b00f4a99dc034668d4135e95c80f4281fc3b768ed314599a2760ade6125799dc2762ade81e5394e92a66a1fc276aad10539ed9044085fa3f74b1ee2b589d2266ad95d21f54c0054a8fd4105f9ae92c63a6fd3877b2125798dd06438cc93a5097c90a4780fd064b8cd1125f99246f8bce11549fda2560a4f93e73b0ee2964bfe2256fd4115e9bc80d4287fc3977b2d1145b9e2560afea39567cc3064d88d7125194eb2d66a3fc396aaf10559edb054083c6397cb7f20845bec205488b')
	XOR_KEY_LEN = 4096

	def __init__(self, *args, **kwargs):
		super(HFS, self).__init__(*args, **kwargs)
		self.entries = []

		self.size = os.stat(self.name).st_size
		self.seek(HFS.CENTRAL_DIRECTORY_END_SIZE, io.SEEK_END)

		self.cdh_offset = -1
		for i in range((2**16) + HFS.CENTRAL_DIRECTORY_END_SIZE):
			if self.read(4) == HFS.CENTRAL_DIRECTORY_END_HEADER:
				self.cdh_offset = self.tell()
				break
			self.seek(self.size - i)

		if self.cdh_offset == -1:
			raise NoCentralDirectoryEndException(self.tell())

		self.cdh = self._read_central_directory_end()
		self.seek(self.cdh.cdr_offset)
		for i in range(self.cdh.cdr_count):
			self.entries.append(self._read_central_directory())

	LOCAL_FILE_STRUCTURE = struct.Struct("<HHHHHIIIHH")
	DECOMPRESSOR = zlib.decompressobj(15)
	BLOCK_SIZE = 4096

	def save_file(self, index, path):
		entry = self.entries[index]
		self.seek(entry.file_offset)
		header = self._read_local_file()
		self.seek(header.offset)
		print("Reading {}".format(header.filename))
		if self.xor_read(4) == b"comp":
			entry.size = struct.unpack("<I", self.xor_read(4))[0]
			decompressor = zlib.decompressobj(15)
			try:
				with open(path, "wb") as f:
					read = 0
					read_size = HFS.BLOCK_SIZE if HFS.BLOCK_SIZE < header.csize else header.csize
					while (True):
						if len(decompressor.unconsumed_tail) > 0:
							f.write(decompressor.decompress(decompressor.unconsumed_tail, HFS.BLOCK_SIZE))
						else:
							remaining = header.csize - read
							f.write(decompressor.decompress(self.xor_read(read_size if remaining > HFS.BLOCK_SIZE else remaining), HFS.BLOCK_SIZE))
							read += read_size
							sys.stdout.write("\r{}".format(read))
							sys.stdout.flush()
						if decompressor.eof or read >= header.csize:
							break
					print("")
					f.write(decompressor.flush())
			except zlib.error:
				print("Failed to decompress: {}\n{}".format(header.filename, traceback.format_exc()))
		else:
			self.seek(header.offset)
			with open(path, "wb") as f:
				read = 0
				read_size = read_size = HFS.BLOCK_SIZE if HFS.BLOCK_SIZE < header.csize else header.csize
				while(True):
					remaining = header.csize - read
					f.write(self.xor_read(read_size if remaining > HFS.BLOCK_SIZE else remaining))
					read += read_size
					sys.stdout.write("\r{}".format(read))
					sys.stdout.flush()
					if read >= header.csize:
						break
				print("")

	def _read_local_file(self):
		if self.read(4) != HFS.LOCAL_FILE_HEADER:
			raise NoLocalFileException(self.tell())
		meta = Bunch()
		(meta.version,
			meta.flag,
			meta.compression,
			meta.mtime,
			meta.mdate,
			meta.crc,
			meta.csize,
			meta.size,
			meta.filename_len,
			meta.extra_len) = HFS.LOCAL_FILE_STRUCTURE.unpack(self.read(HFS.LOCAL_FILE_STRUCTURE.size))
		meta.filename = self.xor_read(meta.filename_len).decode('utf-8')
		meta.extra = self.read(meta.extra_len).decode('utf-8')
		meta.offset = self.tell()
		return meta

	CENTRAL_DIRECTORY_STRUCTURE = struct.Struct("<HHHHHHIIIHHHHHII")

	def _read_central_directory(self):
		if self.read(4) != HFS.CENTRAL_DIRECTORY_HEADER:
			raise NoCentralDirectoryException(self.tell())
		meta = Bunch()
		(meta.version_created,
			meta.version_extractable,
			meta.flag,
			meta.compression,
			meta.mtime,
			meta.mdate,
			meta.crc,
			meta.csize,
			meta.size,
			meta.filename_len,
			meta.extra_len,
			meta.comment_len,
			meta.disk_number,
			meta.internal_attr,
			meta.external_attr,
			meta.file_offset) = HFS.CENTRAL_DIRECTORY_STRUCTURE.unpack(self.read(HFS.CENTRAL_DIRECTORY_STRUCTURE.size))
		meta.filename = self.xor_read(meta.filename_len).decode('utf-8')
		meta.extra = self.read(meta.extra_len).decode('utf-8')
		meta.comment = self.read(meta.comment_len).decode('utf-8')
		return meta

	CENTRAL_DIRECTORY_END_STRUCTURE = struct.Struct("<HHHHIIH")

	def _read_central_directory_end(self):
		meta = Bunch()
		(meta.disk_number,
			meta.cdr_disk,
			meta.cdr_num,
			meta.cdr_count,
			meta.size,
			meta.cdr_offset,
			meta.comment_len) = HFS.CENTRAL_DIRECTORY_END_STRUCTURE.unpack(self.read(HFS.CENTRAL_DIRECTORY_END_STRUCTURE.size))
		meta.comment = self.read(meta.comment_len).decode('utf-8')
		if self.tell() != self.size:
			meta.second_pass = self.read(4)
		return meta

	def xor_read(self, size):
		offset = self.tell()
		b = bytearray(self.read(size))
		for i in range(len(b)):
			b[i] ^= HFS.XOR_KEY[(i + offset) % HFS.XOR_KEY_LEN]
		return bytes(b)


def main():
	parser = argparse.ArgumentParser(description="Extracts Vindictus HFS files.")
	parser.add_argument("--directories", "-d", nargs="*", help="List of directories to find HFS files in.")
	parser.add_argument("--files", "-f", nargs="*", help="List of files that are HFS.")
	parser.add_argument("--find", help="Specify filenames to find")
	args = parser.parse_args()

	if args.directories is None and args.files is None:
		parser.print_help()
		return

	files_to_read = []

	if args.directories is not None:
		for directory in args.directories:
			if not os.path.exists(directory) or not os.path.isdir(directory):
				print("{} is not a directory.".format(directory))
				continue

			for (path, dirs, files) in os.walk(directory):
				for file in files:
					files_to_read.append(path + file)

	if args.files is not None:
		for file in args.files:
			if os.path.exists(file) and os.path.isfile(file):
				files_to_read.append(file)

	hfs_files = {}
	for file in files_to_read:
		try:
			hfs = HFS(file, "rb")
			hfs_filename = os.path.basename(file)
			print("=== {} ===".format(hfs_filename))
			if not os.path.isdir(hfs_filename):
				os.mkdir(hfs_filename)
			for i, entry in enumerate(hfs.entries):
				filename = entry.filename
				if filename[-5:] == ".comp":
					filename = filename[:-5]
				if os.path.basename(filename).lower()[-4:] == ".wav":
					if not os.path.exists(hfs_filename + os.path.sep + filename):
						hfs.save_file(i, hfs_filename + os.path.sep + filename)
			hfs_files[file] = [entry.filename for entry in hfs.entries]
		except HFSException:
			print("{}:\n{}".format(file, traceback.format_exc()))
			continue
		finally:
			hfs.close()

	#with open("names.json", "w") as f:
	#	f.write(json.dumps(hfs_files))

if __name__ == '__main__':
	main()
