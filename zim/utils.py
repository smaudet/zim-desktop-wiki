# -*- coding: utf-8 -*-

# Copyright 2012-2013 Jaap Karssenberg <jaap.karssenberg@gmail.com>


class classproperty(object):
    def __init__(self, func):
        self.func = func

    def __get__(self, obj, owner):
        return self.func(owner)


## Functions for dynamic loading of modules and klasses
import inspect


def get_module(name):
	'''Import a module

	@param name: the module name
	@returns: module object
	@raises ImportError: if the given name does not exist

	@note: don't actually use this method to get plugin modules, see
	L{get_plugin_module()} instead.
	'''
	# __import__ has some quirks, see the reference manual
	mod = __import__(name)
	for part in name.split('.')[1:]:
		mod = getattr(mod, part)
	return mod


def lookup_subclass(module, klass):
	'''Look for a subclass of klass in the module

	This function is used in several places in zim to get extension
	classes. Typically L{get_module()} is used first to get the module
	object, then this lookup function is used to locate a class that
	derives of a base class (e.g. PluginClass).

	@param module: module object
	@param klass: base class

	@note: don't actually use this method to get plugin classes, see
	L{get_plugin()} instead.
	'''
	subclasses = lookup_subclasses(module, klass)
	if len(subclasses) > 1:
		raise AssertionError, 'BUG: Multiple subclasses found of type: %s' % klass
	elif subclasses:
		return subclasses[0]
	else:
		return None


def lookup_subclasses(module, klass):
	'''Look for all subclasses of klass in the module

	@param module: module object
	@param klass: base class
	'''
	subclasses = []
	for name, obj in inspect.getmembers(module, inspect.isclass):
		if issubclass(obj, klass) \
		and obj.__module__.startswith(module.__name__):
			subclasses.append(obj)

	return subclasses


#### sorting functions
import locale
import re
import unicodedata


_num_re = re.compile(r'\d+')


def natural_sort(list, key=None):
	'''Natural sort a list in place.
	See L{natural_sort_key} for details.
	@param list: list of strings to be sorted
	@param key: function producing strings for list items
	'''
	if key:
		def func(s):
			s = key(s)
			return (natural_sort_key(s), s)
	else:
		func = lambda s: (natural_sort_key(s), s)
	list.sort(key=func)


def natural_sorted(iter, key=None):
	'''Natural sort a list.
	See L{natural_sort_key} for details.
	@param iter: list or iterable of strings to be sorted
	@param key: function producing strings for list items
	@returns: sorted copy of the list
	'''
	l = list(iter) # cast to list and implicit copy
	natural_sort(l, key=key)
	return l


def natural_sort_key(string, numeric_padding=5):
	'''Format string such that it gives 'natural' sorting on string
	compare. Will pad any numbers in the string with "0" such that "10"
	sorts after "9". Also includes C{locale.strxfrm()}.

	@note: sorting not 100% stable for case, so order between "foo" and
	"Foo" is not defined. For this reason when sort needs to be absolutely
	stable it is advised to sort based on tuples of
	C{(sort_key, original_string)}. Or use either L{natural_sort()} or
	L{natural_sorted()} instead.

	@param string: the string to format
	@param numeric_padding: number of digits to use for padding
	@returns: string transformed to sorting key
	'''
	templ = '%0' + str(numeric_padding) + 'i'
	string = _num_re.sub(lambda m: templ % int(m.group()), string)
	if isinstance(string, unicode):
		string = unicodedata.normalize('NFKC', string)
		# may be done by strxfrm as well, but want to be sure
	string = locale.strxfrm(string.lower())
	return string.decode('utf-8') # not really utf-8, but 8bit bytes


####

# Python 2.7 has a weakref.WeakSet, but using this one for compatibility with 2.6 ..

import weakref
class WeakSet(object):

	def __init__(self):
		self._refs = []

	def __iter__(self):
		return (
			obj for obj in
					[ref() for ref in self._refs]
							if obj is not None
		)

	def add(self, obj):
		ref = weakref.ref(obj, self._del)
		self._refs.append(ref)

	def _del(self, ref):
		try:
			self._refs.remove(ref)
		except ValueError:
			pass

	def discard(self, obj):
		for ref in self._refs:
			if ref() == obj:
				self._refs.remove(ref)
