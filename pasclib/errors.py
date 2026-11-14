"""Error types shared by the compiler and the VM."""


class CompileError(Exception):
	def __init__(self, fname, line, col, msg):
		Exception.__init__(self, msg)
		self.fname = fname
		self.line = line
		self.col = col
		self.msg = msg

	def __str__(self):
		return '%s:%d:%d: error: %s' % (self.fname, self.line, self.col, self.msg)


# FPC run-time error numbers and their descriptions.
RTE_NAMES = {
	1: 'Invalid function number',
	2: 'File not found',
	3: 'Path not found',
	4: 'Too many open files',
	5: 'Access denied',
	100: 'Disk read error',
	101: 'Disk write error',
	102: 'File not assigned',
	103: 'File not open',
	104: 'File not open for input',
	105: 'File not open for output',
	106: 'Invalid numeric format',
	107: 'Invalid enumeration value',
	200: 'Division by zero',
	201: 'Range check error',
	202: 'Stack overflow error',
	203: 'Heap overflow error',
	204: 'Invalid pointer operation',
	205: 'Floating point overflow',
	206: 'Floating point underflow',
	207: 'Invalid floating point operation',
	215: 'Arithmetic overflow',
	216: 'General protection fault (nil or invalid pointer)',
}


# With 'uses math' fpc links sysutils, which turns run-time errors into
# exceptions: the program dies with "An unhandled exception occurred"
# and exit status 217.  Exception class and message per error number:
EXCEPTIONS = {
	2: ('EInOutError', 'File not found'),
	3: ('EInOutError', 'Path not found'),
	5: ('EInOutError', 'Access denied'),
	100: ('EInOutError', 'Disk read error'),
	101: ('EInOutError', 'Disk write error'),
	102: ('EInOutError', 'File not assigned'),
	103: ('EInOutError', 'File not open'),
	104: ('EInOutError', 'File not open for input'),
	105: ('EInOutError', 'File not open for output'),
	106: ('EInOutError', 'Invalid input'),
	107: ('EInOutError', 'Unknown Run-Time error : 107'),
	200: ('EDivByZero', 'Division by zero'),
	201: ('ERangeError', 'Range check error'),
	202: ('EStackOverflow', 'Stack overflow'),
	203: ('EOutOfMemory', 'Out of memory'),
	204: ('EInvalidPointer', 'Invalid pointer operation'),
	205: ('EOverflow', 'Floating point overflow'),
	206: ('EUnderflow', 'Floating point underflow'),
	207: ('EInvalidOp', 'Invalid floating point operation'),
	215: ('EIntOverflow', 'Arithmetic overflow'),
	216: ('EAccessViolation', 'Access violation'),
}


class RunError(Exception):
	"""A Pascal run-time error; code is the FPC run-time error number."""
	def __init__(self, code):
		Exception.__init__(self, RTE_NAMES.get(code, 'Run-time error'))
		self.code = code


class Halt(Exception):
	def __init__(self, code):
		Exception.__init__(self, 'halt')
		self.code = code
