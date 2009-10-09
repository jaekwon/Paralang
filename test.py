from para import TokenStream, parse_string, interpret

print parse_string("""[foo bar baz]""")
print parse_string("""[foo bar baz [blah blah] ]""")
print parse_string("""[foo:1 bar:2 baz:3]""")
print parse_string("""[foo:1 bar:2 baz:[1 2 3]]""")
print parse_string("""[[1][2][3]]""")
print parse_string("""[
  a_func = {(a b c)
    bar = a+b+c
    return: self.bar
  }
  return: self.a_func(1 2 3)
]""")

def assert_fails(string):
	try:
		parse_string(string)
	except:
		pass
	else:
		raise AssertionError, 'did not fail to parse: %s' % string

## these error...
assert_fails("""[[1][2][3]:4]""")


## interpreting
def do_interpret(string):
	parsed = parse_string(string)
	print str(parsed)
	#print interpret(parsed)

do_interpret("""
{
	\. = {
		(left, right)
		key = left
		target = right
	}

	sys = [
		stdout = stdout
	]

	foo = [1 2 3]
	
	bar = self.foo

	sys.stdout = self.bar

}""")
