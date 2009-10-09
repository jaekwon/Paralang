from para import TokenStream, parse_string, interpret

def assert_computes_to(code, output):
	parsed = parse_string(code)
	try:
		computed = interpret(parsed)
		expected = parse_string(output)
		if str(computed) != str(expected):
			print "FAIL"
			print "code: " + str(code)
			print "parsed: " + str(parsed)
			print "computed: " + str(computed)
			print "expected: " + str(expected)
			import pdb; pdb.set_trace()
	except Exception, e:
		print "FAILED TO INTERPRET"
		print "parsed: " + str(parsed)
		raise

code = """
[

	!debugger
	foo = {(a b c=4)
		a = b+c
		return: a
	}

	return: foo(a:1 b:2 c:3)

]

"""
assert_computes_to(code, "5")


code = """
{
	foo = [a:1 b:2]
    foo.a = 3
}
""" # this.foo does not work because it's jank. what do we do?
assert_computes_to(code, "[__name__:__main__ foo:[a:1 b:2 a:3]]")


code = """
{
	foo = [1 2]
    bar = self.foo
}
"""
assert_computes_to(code, "[__name__:__main__ foo:[1 2 ] bar:[1 2 ] ]")


code = """
{
	foo = [1 2]
	bar = [foo]
}

"""
assert_computes_to(code, "[__name__:__main__ foo:[1 2] bar:[[1 2]]]")


code = """
{
	sys = [
		stdout = 'stdout
	]
	foo = [1 2 3]
	bar = [x:foo y:foo z:foo]
	baz = bar.x
}

"""
assert_computes_to(code, "[__name__:__main__ sys:[stdout:stdout ] foo:[1 2 3 ] bar:[x:[1 2 3 ] y:[1 2 3 ] z:[1 2 3 ] ] baz:[1 2 3 ] ]")


code = """
{
	foo = [1 2 3]
	bar = [x:foo y:foo z:foo]
	baz = bar.x
	return: baz
}

"""
assert_computes_to(code, "[1 2 3]")


code = """
{
	foo = [a: [z:1 x:2 y:3] b: [z:2 x:3 y:1]]
	bar = [aaa:foo.a bbb:foo.b]
	baz = [bar.aaa.z bar.bbb.y]
	return: baz
}
"""
assert_computes_to(code, "[1 1]")


code = """
{
	foo = bar
	bar = 1
	return: foo
}
"""
assert_computes_to(code, "1")

code = """
{
	foo = [bar baz]
	bar = 1
	baz = 2
	return: foo
}
"""
assert_computes_to(code, "[1 2]")


code = """
{
	foo = bar
	bar = baz
	baz = 'booya
	return: foo
}
"""
assert_computes_to(code, "booya")
