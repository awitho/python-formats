
# coding=utf-8

from enum import Enum

class Region(Enum):
	USA = 0
	JAPAN = 1
	EUROPE = 2
	AUSTRALIA = 3
	SEA = 4
	CHINA = 5
	AMERICAS = 6
	CHINA = 7
	GERMANY = 8
	FRANCE = 9
	NETHERLANDS = 10
	ITALY = 11
	KOREA = 12
	SPAIN = 13
	ARGENTINA = 14
	WORLDWIDE = 255

	def name(self):
		return Region.names[self]

	def short_name(self):
		return Region.short_names[self]

Region.names = {
	Region.USA: "United States of America",
	Region.JAPAN: "Japan",
	Region.EUROPE: "Europe",
	Region.AUSTRALIA: "Australia",
	Region.SEA: "South East Asia",
	Region.CHINA: "China",
	Region.GERMANY: "Germany",
	Region.FRANCE: "France",
	Region.NETHERLANDS: "Netherlands",
	Region.ITALY: "Italy",
	Region.KOREA: "Korea",
	Region.SPAIN: "Spain",
	Region.ARGENTINA: "Argentina",
	Region.WORLDWIDE: "World Wide"
}

# ISO-3166 names
Region.short_names = {
	Region.USA: "US",
	Region.JAPAN: "JP",
	Region.EUROPE: "EU", # not in iso3166
	Region.AUSTRALIA: "AU",
	Region.SEA: "SA", # not in iso3166
	Region.CHINA: "CN",
	Region.GERMANY: "DE",
	Region.FRANCE: "FR",
	Region.NETHERLANDS: "NL",
	Region.ITALY: "IT",
	Region.KOREA: "KR",
	Region.SPAIN: "ES",
	Region.ARGENTINA: "AR",
	Region.WORLDWIDE: "WW" # not in iso3166
}
