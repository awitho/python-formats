
# coding=utf-8

import io

from enum import Enum

from iim import IIM, IIMError
from structio import BytesStructIO, Endianess
from util import Bunch


class PhotoshopError(Exception):
	pass


class ResourceType(Enum):
	ImageMeta = 0x3E8
	PrintInfo = 0x3E9
	PageFormat = 0x3EA
	ColorTable = 0x3EB
	ResolutionInfo = 0x3ED
	AlphaChannels = 0x3EE
	DisplayInfo = 0x3EF
	Caption = 0x3F0
	BorderInfo = 0x3F1
	BackgroundColor = 0x3F2
	PrintFlags = 0x3F3
	GrayscaleHalftoningInfo = 0x3F4
	ColorHalftoningInfo = 0x3F5
	DuotoneHalftoningInfo = 0x3F6
	GrayscaleTransferFunction = 0x3F7
	ColorTransferFunction = 0x3F8
	DuotoneTransferFunction = 0x3F9
	DuotoneImageInfo = 0x3FA
	EffectBW = 0x3FB
	Obsolete1 = 0x3FC
	EPSOptions = 0x3FD
	QuickMaskInfo = 0x3FE
	Obsolete2 = 0x3FF
	LayerStateInfo = 0x400
	WorkingPath = 0x401
	LayerGroupInfo = 0x402
	Obsolete3 = 0x403
	IPTCInfo = 0x404
	ImageMode = 0x405
	JPEGQuality = 0x406
	GridGuideInfo = 0x408
	Thumbnail4_0 = 0x409
	CopyrightFlag = 0x40A
	URL = 0x40B
	Thumbnail5_0 = 0x40C
	GlobalAngle = 0x40D
	ColorSamplers = 0x40E
	ICCProfile = 0x40F
	Watermark = 0x410
	ICCUntaggedProfile = 0x411
	EffectsVisible = 0x412
	SpotHalftone = 0x413
	DocumentIDSeeds = 0x414
	UnicodeAlphaNames = 0x415
	IndexedColorTableCount = 0x416
	TransparencyIndex = 0x417
	GlobalAltitude = 0x419
	Slices = 0x41A
	WorkflowURL = 0x41B
	JumpToXPEP = 0x41C
	AlphaIdentifiers = 0x41D
	URLList = 0x41E
	VersionInfo = 0x421
	EXIFData1 = 0x422
	EXIFData3 = 0x423
	XMPMetadata = 0x424
	CaptionDigest = 0x425
	PrintScale = 0x426
	PixelAspectRatio = 0x428
	LayerComps = 0x429
	AlternateDuotoneColors = 0x42A
	AlternateSpotColors = 0x42B
	LayerSelectionID = 0x42D
	HDRToningInfo = 0x42E
	PrintInfo_CS2 = 0x42F
	LayerGroupsEnabled = 0x430
	ColorSamplersResource = 0x431
	MeasurementScale = 0x432
	TimelineInfo = 0x433
	SheetDisclosure = 0x434
	DisplayInfo_CS3 = 0x435
	OnionSkins = 0x436
	CountInfo = 0x438
	PrintInfo_CS5 = 0x43A
	PrintStyle = 0x43B
	MacNSPrintInfo = 0x43C
	WindowsDEVMODE = 0x43D
	AutosavePath = 0x43E
	AutosaveFormat = 0x43F
	PathSelectionState = 0x440
	ClippingPathName = 0xBB7
	OriginPathInfo = 0xBB8
	ImageReadyVariables = 0x1B58
	ImageReadyDataset = 0x1B59
	ImageReadyDefaultState = 0x1B59
	ImageReady7RolloverState = 0x1B5B
	ImageReadyRolloverState = 0x1B5C
	ImageReadySaveLayerSettings = 0x1B5D
	ImageReadyVersion = 0x1B5E
	LightroomWorkflow = 0x1F40
	PrintFlagsInfo = 0x2710


class Resource(Bunch):
	def __init__(self, handle):
		self.handle = handle
		self.parse()
		del self.handle

	def parse(self):
		raw = self.handle
		raw.set_endian(Endianess.BIG)
		if raw.read(4) != b"8BIM":
			raise PhotoshopError("Couldn't find header.")
		self.id = raw.read_ushort()
		try:
			self.id = ResourceType(self.id)
		except ValueError:
			print("Unknown resource id 0x{:x}".format(self.id))
		str_len = raw.read_ubyte()
		if str_len % 2 != 0:
			str_len += 1
		if str_len == 0:
			raw.seek(1, io.SEEK_CUR)
		else:
			self.name = raw.read(str_len)
		self.data = raw.read(raw.read_uint())
		if self.id == ResourceType.IPTCInfo and len(self.data) > 0:
			raw = BytesStructIO(self.data)
			raw.set_endian(Endianess.BIG)
			try:
				self.data = IIM.from_structio(raw)
			except IIMError:
				pass
		if raw.tell() % 2 != 0:
			raw.seek(1, io.SEEK_CUR)

	@classmethod
	def from_structio(cls, buf):
		return cls(buf)
