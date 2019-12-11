
# coding=utf-8

class Bunch(dict):
	def __getattr__(self, key):
		return self[key]

	def __setattr__(self, key, val):
		self[key] = val

	def __delattr__(self, key):
		del self[key]
