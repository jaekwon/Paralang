# generated with http://github.com/jaekwon/jae-python/blob/master/outline.py

def assert_sorted(lst):

def is_protein(obj):

def assert_protein(obj, message=None):

class RControl(object):
	"""
		keyz = {WHERE : [ (WHO WRITE WHAT), (WHO READ WHAT), ... ],
				WHERE : [ (WHO WRITE WHAT), ...
	"""

	def __init__(self):

	def write(self, where, what, who):

	def read(self, where, who):
		""" returns the value to read, or None if no versions exist """

	def serialize(self):
		""" returns a list of (WHERE, WHAT) that were written to it.
			order of items by the same WHO is undefined. """

	def kill_one(self, who):

	def kill_some(self, history_items):
		""" kill some of these assuming that all these happened
			after a write that became invalidated. return the remainder.
			Essentially get all the READs in front and return everything after """

	def copy(self):

	def __len__(self):

class Protein(object):
	"""
		An AList with support for 'self' and 'this'.
		It's also an execution context while the Protein is getting synthesized.
		It's usually referred to via 'self' in your code.
		It's prototypical so if you 'self.dot_get', it will go up the parent chain.
	"""

	def __init__(self, order, parent, type='['):
		"""
			order: can be a string, but it must be lexically sortable
			parent: the parent Protein in which this Protein is born.
		"""

	@classmethod
	def make_guid(cls, order, parent):
		""" 
			guid does not change say even if the parent context changes.
			this makes closures and prototyping work seamlessly."""

	def child_guid(self, child_order):

	def copy_from(self, source, who):

	def dot_get(self, key, who):

	def set(self, key, value, who):

	def fetch(self, key, who):

	def __iter__(self):

	def __nonzero__(self):

	def __len__(self):

	def __contains__(self, key):

	def contains(self, key, who):

	def __str__(self, skip=None):

class ParseError(Exception):

def assert_true(condition, message):

def assert_immutable(o):

def is_immutable(o):
	"""
		even ALists are immutable if they have a 'return' keyed object that is
		immutable (recursive definition)
	"""

def assert_maybe_immutable(o):

def is_maybe_immutable(o):
	"""
		An AList that calls the '.' dot operator would upon interpretation
		get assigned 'target' and 'key' keys. That combo may be immutable, though
		we don't know yet.
	"""

def assert_number(o):

def is_number(o):

def assert_string(o):

def is_string(o):

def assert_symbol(o, escaped=None):

def is_symbol(o, escaped=None):

def unescape_symbol(o):

def escape_symbol(o):

def assert_expression(o):

def is_expression(o):

class LazyPointer(object):
	""" A way to reference objects remotely. When used, a copy of the remote
		object is fetched from the source
	"""

	def __init__(self, target_id):

	def deref(self, context):

class AList(object):

	def __init__(self, type):

	def dot_get(self, key):

	def get(self, key):

	def item_at(self, index):

	def set(self, key, value):

	def copy(self):
		""" returns a shallow copy of this AList. this means the two AList keys/values will be shared objects.
			The returned object has a new unique ID. """

	def clone(self):
		""" like copy, but lazy pointers are used so that self can be transfered over the wire """

	def __nonzero__(self):

	def __len__(self):

	def __iter__(self):

	def __str__(self, skip=None):

	def __contains__(self, value):

class Expression(object):
	"""
		An expression doesn't travel across the wire to differnt processes when transfering code, usually 
		it's decoded into an AList.

		During code parsing, expressions that are ALists or immutable get returned as they are (not wrapped in an Expression object)
	"""

	def __init__(self, left, operator, right):

	def to_alist(self):

class TokenStream(object):

	def __init__(self, string):

	def next_char(self):

	def next_nonwhite(self):

	def consume_whitespaces(self):

	def push_char(self, char):

	def __iter__(self):

	def _next(self):
		"""
			does not care about rollback checkpoints
			does not care about assertions.
			basically, call this at your own risk
		"""

		def collect_token(type):

	def push(self, token):
		""" push back a token """

	def next(self, type=None, values=None):
		""" returns the next token """

	def peek(self, index, type=None, values=None):
		""" peeks at the next index'th token to return (starting at 0 being the next) """

	def __str__(self):
		""" good for debugging """

	@contextmanager
	def checkpoint(self, name):
		""" to be used with with_statement.
			
			with stream.checkpoint():
				stream.next()
				stream.peek(0)
				raise Foo

			will automatically roll back the stream for you upon exception. 
			will eat the exception. 
		"""

def parse_string(string):
	""" parses the string and returns a bunch of tokens.
	"""

	def parse_symbol(stream):
		""" 
			returns what the symbol should be, a string, int, ...
		"""

	def parse_number(stream):

	def parse_alist(stream):
		"""
			alist:
				OPEN_ALIST
				key ASSIGN value | value
				...
				CLOSE_ALIST
		"""

	def parse_key(stream):
		"""
			KEY: EXPRESSION.SYMBOL | EXPRESSION@NUMBER | SYMBOL
		"""

	def parse_value(stream):
		"""
			VALUE: EXPRESSION
		"""

	def parse_expression(stream, prior_left=None, prior_operator=None, prior_right=None):
		"""
			(expression)
			expression INFIX_OP expression
			expression # expression (spaces optional)
			expression . symbol
			expression @ expression
			expression (alist) <- function call
			expression [alist] <- indexing
			expression {alist} <- reserved
			alist
			symbol
		"""

class BuiltinOperator(object):

	def operate(self, context, origin, who):

class DotGetOperator(BuiltinOperator):

	@classmethod
	def operate(cls, context, origin, who):

class FetchOperator(BuiltinOperator):

	@classmethod
	def operate(cls, context, origin, who):

class PlusOperator(BuiltinOperator):

	@classmethod
	def operate(cls, context, origin, who):

class ReturnException(Exception):
	"""
		Raised by the runtime right before assigning something
		 to the 'return' key, in effect the 'return' object never gets set, 
		 but rather the value is returned via this exception.
	"""

	def __init__(self, return_value):

def number_to_order(number):
	"""
		to make small numbers compact (no 0 padding)
		 but still lexical orderable,
		long numbers are prepended with underscores
	"""

def interpret(src, parent_context=None, order=None, origin=None, is_calling=True, is_lhs=False):
	"""
		Returns the ultimate return value of given source.
		To interpret a symbol is to fetch it from the context chain.

		Returns a (target / key) tuplie if is_lhs.
	"""

def interpret_call_args(context, order, arguments_list, who):
	"""
		given an alist that is 'arguments_list',
		fill in missing arguments // assign desired key on context
	"""

def interpret_protein(alist, context, order, is_calling, is_lhs=False):
	"""
		context: an existing Protein into which the 'alist' will get expressed.
		starts interpreting the alist onto context.
		returns the ultimate return value | (target/key)
	"""

def interpret_symbol(symbol, parent_context, order, origin, is_calling, is_lhs):
	"""
		order: matters when we have to create a continuation...
		origin: where the symbol was found

		returns (target, key) if is_lhs, otherwise returns some single value.
	"""
