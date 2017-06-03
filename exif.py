
# coding=utf-8

import io
import logging
import struct

from enum import Enum

from util import Bunch
from structio import BytesStructIO, Endianess

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class Type(Enum):
	BYTE = 1
	ASCII = 2
	SHORT = 3
	LONG = 4
	RATIONAL = 5
	UNDEFINED = 7
	SLONG = 9
	SRATIONAL = 10

Type.size = {
	Type.BYTE: 1,
	Type.ASCII: 1,
	Type.SHORT: 2,
	Type.LONG: 4,
	Type.RATIONAL: 8,
	Type.UNDEFINED: 1,
	Type.SLONG: 4,
	Type.SRATIONAL: 8
}


class IFDTagType(Enum):
	# Image data
	ImageWidth = 0x100
	ImageHeight = 0x101
	BitsPerSample = 0x102
	Compression = 0x103
	PhotometricInterpretation = 0x106
	Orientation = 0x112
	SamplesPerPixel = 0x115
	PlanarConfiguration = 0x11C
	YCbCrSubSampling = 0x212
	YCbCrPositioning = 0x213
	XResolution = 0x11A
	YResolution = 0x11B
	ResolutionUnit = 0x128
	# Offsets
	StripOffsets = 0x111
	RowsPerStrip = 0x116
	StripByteCounts = 0x117
	JPEGInterchangeFormat = 0x201
	JPEGInterchangeFormatLength = 0x202
	# Image characteristics
	TransferFunction = 0x12D
	WhitePoint = 0x13E
	PrimaryChromaticities = 0x13F
	YCbCrCoefficients = 0x211
	ReferenceBlackWhite = 0x214
	# Other
	DateTime = 0x132
	ImageDescription = 0x10E
	Make = 0x10F
	Model = 0x110
	Software = 0x131
	Artist = 0x13B
	Copyright = 0x8298
	# Tiff stuff
	FillOrder = 0x10A
	Predictor = 0x13D
	ColorMap = 0x140
	TileWidth = 0x142
	TileLength = 0x143
	TileOffsets = 0x144
	TileByteCounts = 0x145
	InkSet = 0x14C
	DotRange = 0x150
	ExtraSamples = 0x152
	# Exif IFD
	# Version
	ExifVersion = 0x9000
	FlashpixVersion = 0xA000
	# Image data characteristics
	ColorSpace = 0xA001
	Gamma = 0xA5000
	# Image configuration
	ComponentsConfiguration = 0x9101
	CompressedBitsPerPixel = 0x9102
	PixelXDimension = 0xA002
	PixelYDimension = 0xA003
	# User info
	MakerNote = 0x927C
	UserComment = 0x9286
	# Related file info
	RelatedSoundFile = 0xA004
	# Date and time
	DateTimeOriginal = 0x9003
	DateTimeDigitized = 0x9004
	OffsetTime = 0x9010
	OffsetTimeOriginal = 0x9011
	OffsetTimeDigitized = 0x9012
	SubSecTime = 0x9290
	SubSecTimeOriginal = 0x9291
	SubSecTimeDigitized = 0x9292
	# Picture-taking conditions
	ExposureTime = 0x829A
	FNumber = 0x829D
	ExposureProgram = 0x8822
	SpectralSensitivity = 0x8824
	OECF = 0x8828
	SensitivityType = 0x8830
	StandardOutputSensitivity = 0x8831
	RecommendedExposureIndex = 0x8832
	ISOSpeed = 0x8833
	ISOSpeedLatitudeyyy = 0x8834
	ISOSpeedLatitudezzz = 0x8835
	ShutterSpeedValue = 0x9201
	ApertureValue = 0x9202
	BrightnessValue = 0x9203
	ExposureBiasValue = 0x9204
	MaxApertureValue = 0x9205
	SubjectDistance = 0x9206
	MeteringMode = 0x9207
	LightSource = 0x9208
	Flash = 0x9209
	FocalLength = 0x920A
	SubjectArea = 0x9214
	FlashEnergy = 0xA20B
	SpatialFrequencyResponse = 0xA20C
	FocalPlaneXResolution = 0xA20E
	FocalPlaneYResolution = 0xA20F
	FocalPlaneResolutionUnit = 0xA210
	SubjectLocation = 0xA214
	ExposureIndex = 0xA215
	SensingMethod = 0xA217
	FileSource = 0xA300
	SceneType = 0xA301
	CFAPattern = 0xA302
	CustomRendered = 0xA401
	ExposureMode = 0xA402
	WhiteBalance = 0xA403
	DigitalZoomRatio = 0xA404
	FocalLengthIn35mmFilm = 0xA405
	SceneCaptureType = 0xA406
	GainControl = 0xA407
	Contrast = 0xA408
	Saturation = 0xA409
	Sharpness = 0xA40A
	DeviceSettingDescription = 0xA40B
	SubjectDistanceRange = 0xA40C
	# Shooting situation
	Temperature = 0x9400
	Humidity = 0x9401
	Pressure = 0x9402
	WaterDepth = 0x9403
	Acceleration = 0x9404
	CameraElevationAngle = 0x9405
	# Other
	ImageUniqueID = 0xA420
	CameraOwnerName = 0xA430
	BodySerialNumber = 0xA431
	LensSpecification = 0xA432
	LensMake = 0xA433
	LensModel = 0xA434
	LensSerialNumber = 0xA435
	# IFD locations
	ExifIFD = 0x8769
	GPSIFD = 0x8825
	InteropIFD = 0xA005
	# Photoshop-specific (atleast that's what the photoshop docs tell me)
	SubIFD = 0x14A
	JPEGTables = 0x1B5
	XMPMetadata = 0x2BC
	IPTCInfo = 0x83BB
	PhotoshopResources = 0x8649
	ICCProfile = 0x8773
	ImageSourceData = 0x935C
	Annotations = 0xC44F
	# Windows Explorer
	XPTitle = 0x9C9B
	XPComment = 0x9C9C
	XPAuthor = 0x9C9D  # Ignored by Windows Explorer if Artist exists
	XPKeywords = 0x9C9E
	XPSubject = 0x9C9F
	# Unknown source, taken from http://www.sno.phy.queensu.ca/~phil/exiftool/TagNames/EXIF.html
	Padding = 0xEA1C
	ISO = 0x8827
	PrintIM = 0xC4A5
	HostComputer = 0x13C
	OffsetSchema = 0xEA1D
	StitchInfo = 0x4748
	Rating = 0x4746
	RatingPercent = 0x4749
	PageName = 0x11D
	# Unknown but encountered
	Unknown301 = 0x301
	Unknown302 = 0x302
	Unknown303 = 0x303
	Unknown320 = 0x320
	Unknown2A00 = 0x2A00
	Unknown5012 = 0x5012
	Unknown5110 = 0x5110
	Unknown5111 = 0x5111
	Unknown5112 = 0x5112


class GPSTagType(Enum):
	VersionID = 0x0
	LatitudeRef = 0x1
	Latitude = 0x2
	LongitudeRef = 0x3
	Longitude = 0x4
	AltitudeRef = 0x5
	Altitude = 0x6
	TimeStamp = 0x7
	Satellites = 0x8
	Status = 0x9
	MeasureMode = 0xA
	DOP = 0xB
	SpeedRef = 0xC
	Speed = 0xD
	TrackRef = 0xE
	Track = 0xF
	ImgDirectionRef = 0x10
	ImgDirection = 0x11
	MapDatum = 0x12
	DestLatitudeRef = 0x13
	DestLatitude = 0x14
	DestLongitudeRef = 0x15
	DestLongitude = 0x16
	DestBearingRef = 0x17
	DestBearing = 0x18
	DestDistanceRef = 0x19
	DestDistance = 0x1A
	ProcessingMethod = 0x1B
	AreaInformation = 0x1C
	DateStamp = 0x1D
	Differential = 0x1E
	HPositioningError = 0x1F

IFDTagType.IFDPointer = {
	IFDTagType.ExifIFD: IFDTagType,
	IFDTagType.GPSIFD: GPSTagType,
	IFDTagType.InteropIFD: IFDTagType,
	IFDTagType.SubIFD: IFDTagType
}


class IFDTag(Bunch):
	"""
	IFDTag are in total 12 bytes and usually start @ 8
	"""
	@classmethod
	def from_structio(cls, raw, tag_type=IFDTagType):
		self = cls()
		self.tag = raw.read_ushort()
		try:
			self.tag = tag_type(self.tag)
		except ValueError:
			pass  # print(self.tag)

		try:
			self.type = Type(raw.read_ushort())
		except ValueError:
			logger.debug("WARNING: Tag had invalid type pretending it's UNDEFINED.")
			self.type = Type.UNDEFINED

		self.count = raw.read_uint()
		total_size = Type.size[self.type] * self.count
		if total_size <= 4:
			self.read(raw)
			raw.seek(max(4 - total_size, 0), io.SEEK_CUR)
		else:
			self.offset = raw.read_uint()
			logger.debug("at {}".format(self.offset))
			old = raw.tell()
			raw.seek(self.offset)
			self.read(raw)
			raw.seek(old)
		return self

	def read(self, raw):
		logger.debug("of type {}#{}".format(self.type, self.count))
		if self.type == Type.UNDEFINED:
			self.value = raw.read(self.count)
		elif self.type == Type.ASCII:
			self.value = raw.read_string()
			try:
				self.value = self.value.decode('ascii')
			except UnicodeDecodeError:
				logger.debug("Fuck you that wasn't ASCII you anus!!!")
		else:
			self.value = []
			for i in range(self.count):
				if self.type == Type.BYTE:
					self.value.append(raw.read_ubyte())
				elif self.type == Type.LONG:
					self.value.append(raw.read_ulong())
				elif self.type == Type.RATIONAL:
					self.value.append((raw.read_ulong(), raw.read_ulong()))
				elif self.type == Type.SHORT:
					self.value.append(raw.read_ushort())
				elif self.type == Type.SLONG:
					self.value.append(raw.read_long())
				elif self.type == Type.SRATIONAL:
					self.value.append((raw.read_long(), raw.read_long()))
			if self.count == 1:
				self.value = self.value[0]
		return self.value

	def __repr__(self):
		s = "<"
		if isinstance(self.tag, int):
			s += "0x{:x}".format(self.tag)
		else:
			s += "{}".format(self.tag)

		s += ":{}".format(self.type)
		if 'value' in self:
			s += ":{}".format(self.value)
		if 'offset' in self:
			s += " @ {}".format(self.offset)
		return s + ">"


class IFD(Bunch):
	"""
	IFD blocks are of size (12 * n) + 2 with an upper bound of 786,422
	"""
	@classmethod
	def from_structio(cls, raw, tag_type=IFDTagType):
		self = cls()
		self.tags = []
		self.offset = raw.tell()
		count = raw.read_ushort()
		logger.debug("with {} IFDTags @ {}".format(count, self.offset))
		try:
			for i in range(count):
				logger.debug("Reading IFDTag#{} @ {}".format(i, raw.tell()))
				tag = IFDTag.from_structio(raw, tag_type=tag_type)
				if tag is not None:
					self.tags.append(tag)
		except struct.error:
			print("Truncated IFDTag")
			return self
		self.next = raw.read_uint()
		return self


class EXIF(Bunch):
	"""
	The actual embedded exif data is based on riff format, so...
	"""
	def __init__(self, handle):
		self.ifd = {}
		with handle as self.handle:
			self.parse()
		del self.handle

	def parse(self):
		raw = BytesStructIO(self.handle.read())
		byte_order = raw.read(2)
		if byte_order == b"II":
			raw.set_endian(Endianess.LITTLE)
		elif byte_order == b"MM":
			raw.set_endian(Endianess.BIG)
		else:
			raise Exception("Invalid byte order '{}'.".format(byte_order))

		if raw.read_ushort() != 42:
			raise Exception("That wasn't 42, byte order might be wrong.")

		# 0th IFD here we go
		raw.seek(raw.read_uint())
		count = 0
		while True:
			logger.debug("Reading IFD#{} @ {}".format(count, raw.tell()))
			self.ifd[count] = IFD.from_structio(raw)
			for tag in self.ifd[count].tags:
				if tag.tag in IFDTagType.IFDPointer:
					logger.debug("Reading IFD['{}'] @ {}".format(tag.tag, tag.value))
					raw.seek(tag.value)
					self.ifd[tag.tag] = IFD.from_structio(raw, tag_type=IFDTagType.IFDPointer[tag.tag])
			if 'next' not in self.ifd[count] or self.ifd[count].next == 0 or self.ifd[count].next >= len(raw.getvalue()):
				break
			infinite_loop = False
			for i in self.ifd:
				if self.ifd[count].next == self.ifd[i].offset:
					infinite_loop = True
					break
			if infinite_loop:
				break
			logger.debug("next IFD at {}".format(self.ifd[count].next))
			raw.seek(self.ifd[count].next)
			count += 1

	@classmethod
	def from_buffer(cls, buf):
		return cls(buf)

	@classmethod
	def from_file(cls, path):
		return cls(open(path, "rb"))
