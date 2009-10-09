# coding=UTF8
from __future__ import with_statement
from utils import randid
from utils import contextmanager
from data import *

"""
	XXX this might be out of date. read the parse_XXX methods for updated syntax

	symbol:
		???, includes 'number', 'string', and others

	protein:
		[|{
		key :|= value | value
		...
		]|}

	key:
		symbol | expression.symbol | expression@number

	value:
		expression
		
	expression:
		(expression)
		symbol
		protein
		expression # expression (spaces optional)
		expression . symbol
		expression @ expression
		expression (protein) <- function call
		expression [protein] <- indexing
		expression {protein} <- reserved
"""

DEBUG = False
STEP = False

# placeholders, need to be reimplemented where you see this
SOURCE_ORDER = '?'
SOURCE_PARENT = None
PARSER_WHO = '¶'

class ParseError(Exception):
	pass

def assert_true(condition, message):
	if not condition:
		raise ParseError(message)

# immutable
def assert_immutable(o):
	assert_true(is_immutable(o), "error, immutable object expected")
def is_immutable(o):
	"""
		even Proteins are immutable if they have a 'return' keyed object that is
		immutable (recursive definition)
	"""
	if o is None or isinstance(o, (basestring, int, long)):
		return True
	else:
		if is_protein(o):
			return 'return' in o.rcontrol.keyz and is_immutabe(o.dot_get('return'))
		# XXX ?? what else is there?
		return False

# maybe immutable
def assert_maybe_immutable(o):
	assert_true(is_maybe_immutable(o), "error, maybe_immutable object expected")
def is_maybe_immutable(o):
	"""
		A Protein that calls the '.' dot operator would upon interpretation
		get assigned 'target' and 'key' keys. That combo may be immutable, though
		we don't know yet.
	"""
	if is_immutable(o):
		return True
	else:
		return '.' in o.get('call')

# number
def assert_number(o):
	assert_true(is_number(o), "error, number expected")
def is_number(o):
	return isinstance(o, (int, long))

# string
def assert_string(o):
	assert_true(is_string(o), "error, string expected")
def is_string(o):
	return isinstance(o, basestring) and o.startswith('"')

# symbol
def assert_symbol(o, escaped=None):
	assert_true(is_symbol(o, escaped), "error, symbol expected")
def is_symbol(o, escaped=None):
	if escaped is None:
		return isinstance(o, basestring) 
	elif escaped:
		return isinstance(o, basestring) and o.startswith("'")
	else:
		return isinstance(o, basestring) and not o.startswith("'")
def unescape_symbol(o):
	assert_true(len(o) > 1, "error, cannot unescape %s" % o)
	return o[1:]
def escape_symbol(o):
	return "'"+o

# expression
def assert_expression(o):
	assert_true(is_expression(o), "error, expression expected")
def is_expression(o):
	return o is None or isinstance(o, (basestring, int, long, Protein, Expression))

class Expression(object):
	"""
		An expression doesn't travel across the wire to differnt processes when transfering code, usually 
		it's decoded into a Protein.

		During code parsing, expressions that are Proteins or immutable get returned as they are (not wrapped in an Expression object)
	"""
	def __init__(self, left, operator, right):
		self.operator = operator
		self.left = left
		self.right = right
		if DEBUG:
			print "  new Expression ( %s %s %s )" % (str(self.left), str(self.operator), str(self.right))

	def to_protein(self):
		# convert left to Protein
		if isinstance(self.left, Expression):
			left = self.left.to_protein()
		else:
			if self.left == 'self': # HACK
				left = 'parent'
			else:
				left = self.left

		# convert right to Protein
		if isinstance(self.right, Expression):
			right = self.right.to_protein()
		else:
			right = self.right

		# operator...
		if self.operator == 'CALL':
			assert_protein(right, 'arguments to a call must be an Protein')
			right.set('call', left, PARSER_WHO + ".2")
			return right
		else:
			protein = Protein(SOURCE_ORDER, SOURCE_PARENT, '[')
			if self.operator == '.':
				protein.set('target', left, PARSER_WHO + ".0")
				assert_symbol(right)
				protein.set('key', escape_symbol(right), PARSER_WHO + ".1")
			else:
				protein.set('left', left, PARSER_WHO + ".0")
				protein.set('right', right, PARSER_WHO + ".1")
			protein.set('call', self.operator, PARSER_WHO + ".2")
			return protein


## PARSING 

OPEN_PROTEIN = {
	'[': ']',
	'(': ')',
	'{': '}',
}
CLOSE_PROTEIN = OPEN_PROTEIN.values()
ASSIGN = [':', '=']
WHITESPACE = [',', '\n', ' ', '\t']
ESCAPE = ['\\']
INFIX_OPERATORS = ['@', '#', '+', '-', '*', '/', '%', '.']
TOKENS = set(OPEN_PROTEIN.keys() + OPEN_PROTEIN.values() + ASSIGN + WHITESPACE + ESCAPE + INFIX_OPERATORS)

OPERATOR_ORDER = {
	'.': 100,
	'@': 100,
	'#': 100,
	'APPLY': 100,
	'CALL': 80, # cuz this.foo(1) should call on (this.foo)
	'*': 60,
	'/': 60,
	'+': 50,
	'-': 50,
	'%': 50,
}
OPERATORS = OPERATOR_ORDER.keys()
DEFAULT_OPERATOR_ORDER = 100000 # when there is no operator, a very high one is assumed.

class TokenStream(object):
	def __init__(self, string):
		self.input = iter(string)
		self.push_back_chars = []
		self.push_back_tokens = []
		self.checkpoints = []

	def next_char(self):
		if self.push_back_chars:
			return self.push_back_chars.pop(0)
		return self.input.next()

	def next_nonwhite(self):
		char = ' '
		while char in WHITESPACE:
			char = self.next_char()
		return char

	def consume_whitespaces(self):
		char = self.next_nonwhite()
		self.push_char(char)

	def push_char(self, char):
		self.push_back_chars.insert(0, char)

	def __iter__(self):
		return self

	def _next(self):
		"""
			does not care about rollback checkpoints
			does not care about assertions.
			basically, call this at your own risk
		"""
		if self.push_back_tokens:
			return self.push_back_tokens.pop(0)
		token_chars = []
		self.consume_whitespaces()

		def collect_token(type):
			to_return = ''.join(token_chars)
			return (type, to_return)

		while True:
			try:
				char = self.next_char()
			except StopIteration:
				if token_chars:
					return collect_token('SYMBOL')
				else:
					raise
			if char in ESCAPE:
				char = self.next_char()
			elif char in WHITESPACE:
				if token_chars:
					return collect_token('SYMBOL')
				else:
					assert_true(False, 'this should never happen')
			elif char in TOKENS:
				if token_chars:
					# oops we need to complete this symbol first.
					self.push_char(char)
					return collect_token('SYMBOL')
				else:
					token_chars.append(char)
					return collect_token('TOKEN')
			token_chars.append(char)

	def push(self, token):
		""" push back a token """
		self.push_back_tokens.insert(0, token)

	def next(self, type=None, values=None):
		""" returns the next token """
		assert type in (None, 'SYMBOL', 'TOKEN'), 'oops, arg "type" for next should be SYMBOL or TOKEN'
		try:
			next_token = self._next()
		except StopIteration, e:
			raise ParseError, 'expected %s %s but stream is incomplete' % (type if type else 'SYMBOL|TOKEN', '|'.join(values) if values else '')
		if self.checkpoints:
			self.checkpoints[-1][1].append(next_token)
		if type is not None:
			assert_true( next_token[0] == type, 'expected %s but got %s' % (type, next_token[1]) )
		if values is not None:
			assert_true( next_token[1] == values or next_token[1] in values, 'expected %s but got %s' % ('|'.join(values), next_token[1]) )
		return next_token

	def peek(self, index, type=None, values=None):
		""" peeks at the next index'th token to return (starting at 0 being the next) """
		assert isinstance(index, int), 'oops, first arg to peek should be an index'
		assert type in (None, 'SYMBOL', 'TOKEN'), 'oops, arg "type" for peek should be SYMBOL or TOKEN'
		need_to_read = index - len(self.push_back_tokens) + 1
		if need_to_read > 0:
			for i in range(need_to_read):
				try:
					self.push_back_tokens.append(self._next())
				except StopIteration, e:
					return ('EOM', 'EOM')
		peek_token = self.push_back_tokens[index]
		if type is not None:
			assert_true( peek_token[0] == type, 'expected %s but got %s' % (type, peek_token[1]) )
		if values is not None:
			assert_true( peek_token[1] == values or peek_token[1] in values, 'expected %s but got %s' % ('|'.join(values), peek_token[1]) )
		return peek_token

	def __str__(self):
		""" good for debugging """
		lines = []
		lines.append('  push_back_chars: %s' % ' '.join(self.push_back_chars))
		lines.append('  push_back_tokens: %s' % ' '.join(str(v) for (type, v) in self.push_back_tokens))
		lines.append('  checkpoints: %s' % ' '.join('<%s>'%(' '.join(str(v) for (type, v) in tokens)) for id, tokens in self.checkpoints))
		return '\n'.join(lines)

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
		depth = len(self.checkpoints)
		if DEBUG:
			if STEP:
				import pdb; pdb.set_trace()
			print " BEGIN _________________________%s%s" % ('|   '*depth, name)
			print str(self)
		context_id = randid()
		self.checkpoints.append( (context_id, []) ) # the 'next' method will append to this list
		try:
			yield context_id
		except ParseError, e:
			# unroll
			last_checkpoint = self.checkpoints.pop()
			assert last_checkpoint[0] == context_id, "oops, control stack got borked. did you mess with rollback checkpoints? expected %s but got %s" % (context_id, last_checkpoint[0])
			self.push_back_tokens = last_checkpoint[1] + self.push_back_tokens
			if DEBUG:
				print " ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~%s%s %s %s" % ('|   '*depth, name, 'FAIL', e.message)
		else:
			last_checkpoint = self.checkpoints.pop()
			assert last_checkpoint[0] == context_id, "oops, control stack got borked. did you mess with rollback checkpoints? expected %s but got %s" % (context_id, last_checkpoint[0])
			if self.checkpoints:
				self.checkpoints[-1][1].extend(last_checkpoint[1])
			if DEBUG:
				print " ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~%s%s %s" % ('|   '*depth, name, 'SUCCESS')
		
def parse_string(string):
	""" parses the string and returns a bunch of tokens.
	"""

	stream = TokenStream(string)

	def parse_symbol(stream):
		""" 
			returns what the symbol should be, a string, int, ...
		"""
		token = stream.peek(0, 'SYMBOL')[1]
		if token[0] in '0123456789':
			return parse_number(stream)
		else:
			stream.next() # eat
			return token

	def parse_number(stream):
		token = stream.next('SYMBOL')[1]
		after_token = stream.peek(0)
		try:
			if after_token[0] == 'TOKEN' and after_token[1] == '.':
				stream.next() # eat
				decimals = stream.next('SYMBOL')
				number = '%s.%s' % (token, decimals[1])
				return float(number)
			else:
				return int(token)
		except:
			raise AssertionError, 'expected number but got %s' % number

	def parse_protein(stream):
		"""
			protein:
				OPEN_PROTEIN
				key ASSIGN value | value
				...
				CLOSE_PROTEIN
		"""
		opener = stream.next('TOKEN', OPEN_PROTEIN)[1]
		protein = Protein(SOURCE_ORDER, SOURCE_PARENT, opener)

		order_index = -1
		while True:
			order_index += 1
			# maybe key
			key = None
			with stream.checkpoint('protein> key:'):
				key = parse_key(stream)
				if isinstance(key, Expression):
					key = key.to_protein()
			# definitely value
			with stream.checkpoint('protein> value'):
				value = parse_value(stream)
				if isinstance(value, Expression):
					value = value.to_protein()
				protein.set(key, value, PARSER_WHO + ".%i"%order_index)
				continue

			# no more key:value | value 
			closer = stream.next('TOKEN', CLOSE_PROTEIN)[1]
			assert_true( closer == OPEN_PROTEIN[opener], 'mismatched parens, expected %s but got %s' % (OPEN_PROTEIN[opener], closer) )
			return protein

	def parse_key(stream):
		"""
			KEY: EXPRESSION.SYMBOL | EXPRESSION@NUMBER | SYMBOL
		"""
		expression = parse_expression(stream)
		if isinstance(expression, Expression):
			# see if it's like expression.symbol or expression@number
			if expression.operator == '.':
				assert_expression(expression.left)
				assert_immutable(expression.right)
				stream.next('TOKEN', ASSIGN) # eat
				return expression
			elif expression.operator == '@':
				assert_expression(expression.left)
				assert_number(expression.right)
				stream.next('TOKEN', ASSIGN) # eat
				return expression
			else:
				raise ParseError, 'cannot have expression with operator %s in LHS' % expression.operator
		elif is_immutable(expression):
			# just a lone symbol on the left
			stream.next('TOKEN', ASSIGN) # eat
			return expression
		else:
			raise ParseError, 'invalid LHS key: %s' % str(expression)

	def parse_value(stream):
		"""
			VALUE: EXPRESSION
		"""
		expression = parse_expression(stream)
		return expression

	def parse_expression(stream, prior_left=None, prior_operator=None, prior_right=None):
		"""
			(expression)
			expression INFIX_OP expression
			expression # expression (spaces optional)
			expression . symbol
			expression @ expression
			expression (protein) <- function call
			expression [protein] <- indexing
			expression {protein} <- reserved
			protein
			symbol
		"""
		peek = stream.peek(0)

		# see if the expression is wrapped in parens.
		if peek[0] == 'TOKEN':
			if peek[1] == '(':
				with stream.checkpoint('expression> (expression)'):
					stream.next('TOKEN', '(') # eat
					expression = parse_expression(stream)
					stream.next('TOKEN', ')') # eat
					return expression

		# the prior left may be given to us.
		if prior_right is None:
			# expression begins with a symbol or a Protein (or an expression, but we can't do that because that would recurse forever)
			left = None
			with stream.checkpoint('expression> symbol'):
				left = parse_symbol(stream)
			if left is None:
				with stream.checkpoint('expression> protein'):
					left = parse_protein(stream)
			assert_true(left is not None, 'parse error, unparseable expression (does not start with a symbol or Protein)')
		else:
			left = prior_right

		# see if it's an infix/CALL/APPLY
		with stream.checkpoint('expression> expression infix expression'):

			infix = None
			with stream.checkpoint('expression> infix'):
				infix = stream.next('TOKEN', INFIX_OPERATORS)[1]
			if infix is None:
				opener = stream.peek(0, 'TOKEN', OPEN_PROTEIN)[1]
				if opener == '(':
					infix = 'CALL'
				elif opener == '[':
					infix = 'APPLY'
				else:
					raise AssertionError, 'EXPRESSION {Protein} is reserved syntax. Did you mean to assign a key to {Protein}?'
			assert_true(infix is not None, 'not an infix')

			if prior_left is not None:
				if OPERATOR_ORDER[prior_operator] >= OPERATOR_ORDER[infix]:
					# the prior_left and left are the left/right of an expression, and that expression is the new prior left
					#                                         (  OLD_LEFT    OLD_OP        LEFT)    OP   ???
					return parse_expression(stream, Expression(prior_left, prior_operator, left), infix)
				else:
					# prior_left and left may not be directly connected, left might be part of a bigger expression
					#                (  OLD_LEFT    OLD_OP                        (        LEFT    OP    ???
					return Expression(prior_left, prior_operator, parse_expression(stream, left, infix))
			else:
				return parse_expression(stream, left, infix)

		if prior_left is not None:
			return Expression(prior_left, prior_operator, left)
		else:
			return left

	try:
		with stream.checkpoint('string> protein'):
			return parse_protein(stream)
		return parse_symbol(stream)
	except ParseError, e:
		print "___________________________"
		print string
		print stream
		print "~~~~~~~~~~~~~~~~~~~~~~~~~~~"
		raise

