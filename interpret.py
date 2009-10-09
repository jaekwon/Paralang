from parse import *
from data import *

DEBUG = True

class BuiltinOperator(object):
	def operate(self, context, origin, who):
		pass

class DotGetOperator(BuiltinOperator):
	@classmethod
	def operate(cls, context, origin, who):
		target = context.dot_get('target', who)
		key = context.dot_get('key', who)
		result = target.dot_get(key, who)
		raise ReturnException(result)

class FetchOperator(BuiltinOperator):
	@classmethod
	def operate(cls, context, origin, who):
		target = context.dot_get('target', who)
		key = context.dot_get('key', who)
		result = target.fetch(key, who)
		raise ReturnException(result)

class PlusOperator(BuiltinOperator):
	@classmethod
	def operate(cls, context, origin, who):
		left = context.dot_get('left', who)
		right = context.dot_get('right', who)
		assert_number(left)
		assert_number(right)
		raise ReturnException(left+right)

BUILTIN_OPERATORS = {
	'.': DotGetOperator,
	'+': PlusOperator,
	'FETCH': FetchOperator}

class ReturnException(Exception):
	"""
		Raised by the runtime right before assigning something
		 to the 'return' key, in effect the 'return' object never gets set, 
		 but rather the value is returned via this exception.
	"""
	def __init__(self, return_value):
		self.return_value = return_value

def number_to_order(number):
	"""
		to make small numbers compact (no 0 padding)
		 but still lexical orderable,
		long numbers are prepended with underscores
	"""
	assert isinstance(number, int) and number >= 0, \
		'only positive numbers can be converted'
	numdigits = len(str(number))
	return '_'*(numdigits-1) + str(number)

########################################
## OK HERE WE GO INTERPRET LOGIC FOLLOWS

def interpret(src, parent_context=None, order=None, origin=None, is_calling=True, is_lhs=False):
	"""
		Returns the ultimate return value of given source.
		To interpret a symbol is to fetch it from the context chain.

		Returns a (target / key) tuplie if is_lhs.
	"""
	if parent_context is None:
		assert order is None, 'parent_context is None, order should be None too'
		order = '.main'
		parent_context = Protein(order, parent=None) # create the root __main__ context
		parent_context.set('__name__', '__main__', '.machine')
	else:
		assert order is not None, 'order must be specified unless parent_context is None'

	try:
		if DEBUG:
			if order == '.main':
				print ""
			print "   %sINTERPRETING %s    *c:%s l:%s o:%s" % \
				('    |'*parent_context._level, src, 1 if is_calling else 0, 1 if is_lhs else 0, order)
			print "   %sON PARENT: %s" % \
				('    |'*parent_context._level, str(parent_context))

		if isinstance(src, LazyPointer):
			src = src.deref(parent_context)

		if is_protein(src):
			if src.type == '{' and not is_calling:
				# return a copy of the src.
				protein_copy = Protein(order, parent_context, src.type)
				protein_copy.copy_from(src, parent_context.child_guid(order))
				result = protein_copy
			else:
				if is_calling:
					context = parent_context
				else:
					context = Protein(order, parent_context, src.type)
				result = interpret_protein(src, context, order, is_calling, is_lhs)
		else:
			if src == None and is_lhs:
				# parent_context is going to set None = something
				return (parent_context, None)
			elif is_symbol(src):
				# order matters because a symbol fetch lambda is a new context protein
				result = interpret_symbol(src, parent_context, order, origin, is_calling, is_lhs)
			elif is_immutable(src):
				result = src

		if DEBUG:
			print "   %s-> %s" % ('    |'*parent_context._level, str(result))
		return result
	except ReturnException, e:
		if parent_context.contains('__name__', '.machine') and parent_context.dot_get('__name__', '.machine') == '__main__':
			return e.return_value
		else:
			raise

def interpret_call_args(context, order, arguments_list, who):
	"""
		given an protein that is 'arguments_list',
		fill in missing arguments // assign desired key on context
	"""
	for args_index, (args_key, args_value) in enumerate(arguments_list):
		if args_key is None: # syntactic sugar, you don't have to say 'argname=None', but just 'argname'
			args_key = args_value
			args_value = None
		else:
			# the default variable
			args_value = interpret(args_value, context, order, origin=arguments_list, is_calling=False)
		assert is_symbol(args_key), 'function argument name must be a symbol'
		assert args_key not in ['this', 'self'], 'reserved keyword this|self'
		assert is_symbol(args_key, escaped=False), 'function default argument list must be of the form \'SYMBOL or SYMBOL:DEFAULT_VALUE'
		if not context.contains(args_key, who):
			# if the value exists in context positionally...
			# [context...     (-3), (-2), (-1) call:{(0 1 2) ...   0 points to -3, 1 points to -2, 2 points to -1. 
			try:
				raise Deprecated, "item_at was the wrong way to do stuff"
				context_arg = context.item_at( -len(arguments_list) ) # remember that context is going to grow each loop
			except IndexError, e:
				raise AssertionError, 'ran out of position args in context %s for function %s' % (context, arguments_list)
			if context_arg[0] is None:
				context.set(args_key, context_arg[1], context.child_guid(order))
			else:
				raise AssertionError, 'function call arg name mismatch'

def interpret_protein(protein, context, order, is_calling, is_lhs=False):
	"""
		context: an existing Protein into which the 'protein' will get expressed.
		starts interpreting the protein onto context.
		returns the ultimate return value | (target/key)
	"""
	assert context
	assert_protein(protein)
	for index, (key, value) in enumerate(protein):
		# stuff that i interpret in this loop get some incrementing order
		my_order = "%s.%s" % (order, number_to_order(index))
		my_key_order = "%s.0_KEY" % my_order
		my_value_order = "%s.1_VALUE" % my_order

		# positional argument stuff.
		if is_calling and index == 0 and key is None and is_protein(value):
			interpret_call_args(context, my_order, value, my_order)
			continue

		# special case when it's the last item and is_lhs:
		if index == len(protein)-1 and is_lhs:
			assert (key, value) == ('call', '.'), 'last item in lhs must be call/.'
			return (context.dot_get('target', my_key_order), context.dot_get('key', my_value_order))

		# plain vanilla assignment
		target, key = interpret(key, context, my_key_order, origin=protein, is_calling=False, is_lhs=True)

		# call or interpret the value or return it
		if key == 'call':
			value = interpret(value, context, my_value_order, origin=protein, is_calling=True)
		elif key == 'return':
			result = interpret(value, context, my_value_order, origin=protein, is_calling=False)
			# super lazy evaluation, value resolution. if the result is an eager object AND
			# it has a 'call', then re-evaluate it.
			# TODO XXX TODO HOW DO WE KNOW? CALL MIGHT BE EMBEDDED DEEP IN THE TREE
			if is_protein(result) and result.type == '[' :
				# note that the 'interpret' below itself may raise a 'return'.
				# TODO is origin right?
				result = interpret(result, context, my_value_order, origin=protein, is_calling=False)
			raise ReturnException(result)
		else:
			try:
				value = interpret(value, context, my_value_order, origin=protein, is_calling=False)
			except ReturnException, e:
				value = e.return_value
			target.set(key, value, my_order)
	return context

def interpret_symbol(symbol, parent_context, order, origin, is_calling, is_lhs):
	"""
		order: matters when we have to create a continuation...
		origin: where the symbol was found

		returns (target, key) if is_lhs, otherwise returns some single value.
	"""
	assert parent_context and origin, 'missing parent_context or origin'
	assert is_symbol(symbol), 'not a symbol'
	my_guid = parent_context.child_guid(order)

	if is_lhs:
		assert symbol not in ['this', 'self'], 'those keywords are reserved'
		return (parent_context, symbol)
	else:
		if symbol in ['this', 'self', 'parent', 'debugger']:
			if symbol == 'this':
				return origin
			elif symbol == 'self':
				return parent_context
			elif symbol == 'parent':
				return parent_context.parent
			elif symbol == 'debugger':
				import pdb;pdb.set_trace() # looks like the italian flag on my VIM. :)
				return symbol

		if is_calling:
			if symbol in BUILTIN_OPERATORS:
				return BUILTIN_OPERATORS[symbol].operate(parent_context, origin, my_guid)
			else:
				# resolution step.
				func_protein = parent_context.fetch(symbol, my_guid)
				assert_protein(func_protein, 'error, cannot call immutable %s' % str(func_protein))
				return interpret(func_protein, parent_context, order, origin, is_calling)
		else:
			if is_symbol(symbol, escaped=True):
				return unescape_symbol(symbol)
			else:
				try:
					return parent_context.fetch(symbol, my_guid)
				except IndexError, e:
					# I introduce to you, the first piece of useful paralang code. 
					"""
						[ // eager_wrapper
						  target: [ // context_wrapper
						    target: { // laz_context
						      <context>
						    }
						    key: 'context
						    call: .
						  ]
						  key: '<symbol>
						  call: FETCH
						]
					"""
					eager_wrapper = Protein(order, parent_context, '[')
					context_wrapper = Protein('0', eager_wrapper, '[')
					lazy_context = Protein('0', context_wrapper, '{')
					context_wrapper.set('target', lazy_context, eager_wrapper.guid + "#0")
					eager_wrapper.set('target', context_wrapper, eager_wrapper.guid + "#1")
					lazy_context.set('context', parent_context, eager_wrapper.guid + "#2")
					context_wrapper.set('key', "'context", eager_wrapper.guid + "#3")
					context_wrapper.set('call', '.', eager_wrapper.guid + "#4")
					eager_wrapper.set('key', escape_symbol(symbol), eager_wrapper.guid + "#5")
					eager_wrapper.set('call', 'FETCH', eager_wrapper.guid + "#6")
					return eager_wrapper
