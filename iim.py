
# coding=utf-8

from enum import Enum

from util import Bunch

class IIMError(Exception):
	pass

class RecordType(Enum):
	Envelope = 1
	Application = 2
	Newsphoto = 3
	Abstract = 6
	PreObjectData = 7
	ObjectData = 8
	PostObjectData = 9

class EnvelopeDataset(Enum):
	ModelVersion = 0
	Destination = 5
	FileFormat = 20
	FileFormatVersion = 22
	ServiceIdentifier = 30
	EnvelopeNumber = 40
	ProductID = 50
	EnvelopePriority = 60
	DateSent = 70
	TimeSent = 80
	CodedCharacterSet = 90
	UNO = 100
	ARMIdentifier = 120
	ARMVersion = 122

class ApplicationDataset(Enum):
	RecordVersion = 0
	ObjectTypeReference = 3
	ObjectAttributeReference = 4
	ObjectName = 5
	EditStatus = 7
	EditorialUpdate = 8
	Urgency = 10
	SubjectReference = 12
	Category = 15
	SupplementalCategory = 20
	FixtureIdentifier = 22
	Keywords = 25
	ContentLocationCode = 26
	ContentLocationName = 27
	ReleaseDate = 30
	ReleaseTime = 35
	ExpirationDate = 37
	ExpirationTime = 38
	SpecialInstructions = 40
	ActionAdvised = 42
	ReferenceService = 45
	ReferenceDate = 47
	ReferenceNumber = 50
	DateCreated = 55
	TimeCreated = 60
	DigitalCreationDate = 62
	DigitalCreationTime = 63
	Origination = 65
	ProgramVersion = 70
	ObjectCycle = 75
	Byline = 80
	BylineTitle = 85
	City = 90
	Sublocation = 92
	Province = 95
	CountryCode = 100
	CountryName = 101
	OriginalTransmissionReference = 103
	Headline = 105
	Credit = 110
	Source = 115
	CopyrightNotice = 116
	Contact = 118
	Caption = 120
	Writer = 122
	RasterizedCaption = 125
	ImageType = 130
	ImageOrientation = 131
	LanguageIdentifier = 135
	AudioType = 150
	AudioSamplingRate = 151
	AudioSamplingResolution = 152
	AudioDuration = 153
	AudioOutcue = 154
	ObjectDataPreviewFileFormat = 200
	ObjectDataPreviewFileFormatVersion = 201
	ObjectDataPreviewData = 202

class PreObjectDataDataset(Enum):
	SizeMode = 10
	MaxSubfileSize = 20
	ObjectDataSizeAnnounced = 90
	MaximumObjectDataSize = 95

class ObjectDataDataset(Enum):
	Subfile = 10

class PostObjectDataDataset(Enum):
	ConfirmedObjectDataSize = 10

RecordType.records = {
	RecordType.Envelope: EnvelopeDataset,
	RecordType.Application: ApplicationDataset,
	RecordType.PreObjectData: PreObjectDataDataset,
	RecordType.ObjectData: ObjectDataDataset,
	RecordType.PostObjectData: PostObjectDataDataset
}

class Tag(Bunch):
	def __init__(self, handle):
		self.handle = handle
		self.parse()
		del self.handle

	def parse(self):
		raw = self.handle
		marker = raw.read_byte()
		if marker != 28:
			raise IIMError("Marker did not match {}".format(marker))
		self.record = RecordType(raw.read_byte())
		self.dataset = raw.read_byte()
		try:
			self.dataset = RecordType.records[self.record](self.dataset)
		except ValueError:
			print("Unknown dataset key {}".format(self.dataset))
		self.data = raw.read(raw.read_short())

	@classmethod
	def from_structio(cls, buf):
		return cls(buf)


class IIM(Bunch):
	def __init__(self, handle):
		self.handle = handle
		self.parse()
		del self.handle

	def parse(self):
		raw = self.handle
		self.tags = []
		while True:
			self.tags.append(Tag.from_structio(raw))
			if raw.tell() >= len(raw.getvalue()):
				break
		return self

	@classmethod
	def from_structio(cls, buf):
		return cls(buf)
