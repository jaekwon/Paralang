from parse import *
from bisect import bisect, insort

DEBUG = False

def assert_sorted(lst):
	old = None
	for item in lst:
		assert old is None or item >= old, 'lst not sorted in ascending order: %s' % str(lst)
		old = item

def is_protein(obj):
	return isinstance(obj, Protein)

def assert_protein(obj, message=None):
	assert is_protein(obj), (message or 'expected a protein but got %s instead' % str(type(obj)))

class RControl(object):
	"""
		keyz = {WHERE : [ (WHO WRITE WHAT), (WHO READ WHAT), ... ],
				WHERE : [ (WHO WRITE WHAT), ...
	"""
	def __init__(self):
		self.keyz = {}

	def write(self, where, what, who):
		history = self.keyz.setdefault(where, [])
		assert_sorted(history)
		insert_index = bisect([who_ for (who_, type_, what_) in history], who)
		if insert_index < len(history):
			# uh oh, there are items in there...
			# kill everything in there until the next WRITE
			remainder = self.kill_some(history[insert_index:], until="WRITE")
			history.append( (who, 'WRITE', what) )
			history[insert_index:] = remainder
		else:
			history.append( (who, 'WRITE', what) )
		assert_sorted(history)

	def read(self, where, who):
		""" returns the value to read, or None if no versions exist """
		history = self.keyz.setdefault(where, [])
		assert_sorted(history)
		read_index = insort(history, (who, 'READ', None))

		# let's see what this read is supposed to see.
		prior_writes = [item for item in history[:read_index] if item[1] == 'WRITE']
		if prior_writes:
			return prior_writes[-1][2] # return the object
		else:
			raise IndexError, 'unknown key %s' % where

	def serialize(self):
		""" returns a list of (WHERE, WHAT) that were written to it.
			order of items by the same WHO is undefined. """
		all_writes = []
		for key, history in self.keyz.iteritems():
			for (who, type, what) in history:
				if type == 'WRITE':
					all_writes.append( (who, key, what) )
		all_writes.sort()
		return [ (key, what) for (who, key, what) in all_writes ]

	def kill_one(self, who):
		raise NotImplementedError, 'woot, i wish i were here.'

	def kill_some(self, history_items):
		""" kill some of these assuming that all these happened
			after a write that became invalidated. return the remainder.
			Essentially get all the READs in front and return everything after """
		while True:
			if not history_items:
				break
			who, type, what = history_items[0]
			if type == 'READ':
				self.kill_one(who)
				history_items.pop(0)
			else:
				break

		return history_items

	def copy(self):
		new_rc = RControl()	
		new_rc.keyz = {}
		for key, value in self.keyz.iteritems():
			new_rc[key] = value.copy() # values are shallow copied.
		return new_rc

	def __len__(self):
		serialized = self.serialize()
		return len(serialized)

class Protein(object):
	"""
		A ubiquitous data structure with support for 'self' and 'this'.
		It's also an execution context while the Protein is getting synthesized.
		It's usually referred to via 'self' in your code.
		It's prototypical so if you 'self.dot_get', it will go up the parent chain.
	"""

	def __init__(self, order, parent, type='['):
		"""
			order: can be a string, but it must be lexically sortable
			parent: the parent Protein in which this Protein is born.
		"""
		self.type = type
		self.order = order
		self.parent = parent
		self.guid = self.make_guid(order, parent)
		self.space = parent.space if parent else {} # the machine space of id->object
		self.space[self.guid] = self
		self.rcontrol = RControl()

		# debug state
		self._level = 0 if parent is None else parent._level + 1

	@classmethod
	def make_guid(cls, order, parent):
		""" 
			guid does not change say even if the parent context changes.
			this makes closures and prototyping work seamlessly."""
		if not parent:
			return order
		return "%s.%s" % (parent.guid, order)

	def child_guid(self, child_order):
		return Protein.make_guid(child_order, self)

	def copy_from(self, source, who):
		if is_protein(source):
			for key, value in source:
				self.set(key, value, who)
		elif isinstance(source, Protein):
			self.rcontrol = source.rcontrol.copy()

	def dot_get(self, key, who):
		return self.rcontrol.read(key, who)

	def set(self, key, value, who):
		self.rcontrol.write(key, value, who)

	def fetch(self, key, who):
		try:
			return self.dot_get(key, who)
		except: # TODO be specific
			if self.parent:
				return self.parent.fetch(key, who)
			else:
				raise

	def __iter__(self):
		serialized = self.rcontrol.serialize()
		return iter(serialized)

	def __nonzero__(self):
		return True

	def __len__(self):
		return len(self.rcontrol)

	def __contains__(self, key):
		assert False, 'do not use this, we need to make a record of the read.'

	def contains(self, key, who):
		try:
			result = self.dot_get(key, who)
		except IndexError, e:
			return False
		return result

	def __str__(self, skip=None):
		# print ref if self was already printed
		if skip is None:
			skip = []
		else:
			skip = list(skip)

		if self in skip:
			return '<Protein@%s>' % self.order
		else:
			skip.append(self)

		lines = []
		if DEBUG:
			lines.append('%s@%s ' % (self.type, self.order))
		else:
			lines.append(self.type)
		for key, value in self.rcontrol.serialize():
			if key:
				if not is_protein(key):
					lines.append(str(key))
				else:
					lines.extend(key.__str__(skip).split('\n'))
				lines.append(':')
			if not is_protein(value):
				lines.append(str(value))
			else:
				lines.extend(value.__str__(skip).split('\n'))
			lines.append(' ')
		closer = {'[': ']', '(': ')', '{': '}'}
		lines.append(closer[self.type])
		return ''.join(lines)


class LazyPointer(object):
	""" A way to reference objects remotely. When used, a copy of the remote
		object is fetched from the source
	"""
	def __init__(self, target_id):
		assert_protein(parent, "parent must be an AList instance" )
		self.target_id = target_id
		# self.target # don't set it until the target is fetched

	def deref(self, context):
		if hasattr(self, 'target'):
			return self.target
		else:
			self.target = context.fetch(self.target_id)
			return self.target
