"""Limits for the style warnings that pasc -w reports.

This is the one place to tune them: change a number here, or set a check
to None (or False) to turn it off.  The limits listed in 'enforced' are
compile errors instead of warnings, unless pasc (or pascdb) is run with -L.
"""

LIMITS = {
	# a source line longer than this (tabs count as 8 columns)
	'line_length': 100,
	# lines in the body of a procedure or function, between begin and end:
	# a longer body is probably not split into subproblems
	'routine_body_lines': 40,
	# lines in the body of the main program
	'main_body_lines': 40,
	# parameters of a procedure or function: more suggests a record or an
	# array should be used instead
	'parameters': 6,
	# limits enforced as compile errors (pasc -L and pascdb -L turn them
	# into warnings shown with -w); the others are always warnings (-w)
	'enforced': ('loops', 'nested_loops', 'nested_structures', 'consecutive_ifs'),
	# loops (while, repeat, for) in one procedure, function or main program
	'loops': 4,
	# loops nested inside loops
	'nested_loops': 2,
	# control structures (if, case, while, repeat, for) nested inside
	# each other; an 'else if' does not nest
	'nested_structures': 6,
	# if statements in a row (an if ... else if ... chain counts as one)
	'consecutive_ifs': 6,
	# two routines whose bodies are the same (up to the names of their
	# parameters and locals) and have at least this many tokens
	'duplicate_min_tokens': 12,
	# the same statement, or group of up to 'repeat_max_group' statements,
	# written this many times in a row (perhaps instead of a loop or a
	# procedure); numbers may differ between the copies
	'repeat_times': 3,
	'repeat_max_group': 4,
	'repeat_min_tokens': 4,
	# if c then x := true else x := false (or result := ...): assign c
	'boolean_if': True,
	# x = True, x <> False, ...: use x or not x
	'boolean_compare': True,
	# if/while/for bodies must be written between begin and end
	'begin_end': True,
	# 'end else' on one line: else goes on its own line, under the end
	'else_own_line': True,
	# begin ... end of a block written on a single line (allowed for the
	# statements of a case branch)
	'begin_end_lines': True,
	# begin on a line of its own after then, do or else (it goes at the
	# end of that line; a case branch may have begin on its own line)
	'begin_same_line': True,
	# for loop that sets a boolean when it finds something but keeps going
	'search_loop': True,
	# routine taking an array and an index used only as a[i]: pass a[i]
	'array_index_param': True,
	# routine taking an array and its number of elements: use a record
	'array_count_param': True,
	# naming style
	'const_uppercase': True,	# constants and enumeration values start uppercase
	'type_uppercase': True,		# type names start uppercase
	'var_lowercase': True,		# variables, parameters and fields are all lowercase
	'routine_lowercase': True,	# procedure and function names are all lowercase
	'consistent_case': True,	# a name is always written as declared
}
