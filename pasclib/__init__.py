"""pasc: an interpreter for the restricted Free Pascal subset of the course.

Source -> tokens (lexer) -> syntax tree (parser) -> checked bytecode
(compiler) -> execution on a stack VM (vm).
"""

VERSION = '1.5'
