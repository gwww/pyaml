"""YAML Macros library"""

"""
Entry point for parsing YAML and picking out the Python
code to run.

Running the code is YAML "aware" meaning that indents are preserved.
"""

import io
import logging
import re
import sys
import textwrap
from collections import namedtuple
from enum import Enum

import yaml

LOG = logging.getLogger(__name__)

LineType = Enum("LineType", "REGULAR COMMENT INCLUDE EXEC EVAL")
Token = namedtuple("Token", "line_type prefix match postfix")


def pyaml_file(filename, reformat=True, directory="."):
    """Convert macros in YAML file to pure YAML."""
    with open(filename) as stream:
        return _pyaml(stream, reformat, directory)


def pyaml_string(yaml_str, reformat=True, directory="."):
    """Convert macros in YAML string to pure YAML."""
    with io.StringIO(yaml_str) as stream:
        return _pyaml(stream, reformat, directory)


def _pyaml(stream, reformat, directory):
    sys.path.insert(0, directory)
    processor = Pyaml(stream)
    lines = processor.load()
    if not processor.last_error and reformat:
        lines = processor.dump()
    return (lines, processor.last_error)


class Pyaml:
    """Support Python embedded in YAML."""

    _re_exec_one_line = re.compile(
        r"""            # Exec block with open/close tag on single line
            \s*         # Can start with any number of spaces
            @\+         # Match the block open tag "@+"
            (.+)        # Capture the expression to exec
            \+@         # Match the exec close tag "%@"
            \s*$        # Any extra spaces matched after tag
        """,
        re.VERBOSE,
    )
    _re_exec_open = re.compile(
        r"""            # Multi-line exec start
            \s*         # Can start with any number of spaces
            @\+         # Match the block open tag "@+"
            \s*$        # Any extra spaces matched after tag
            ()()        # Empty captures (so same capture group as eval)
        """,
        re.VERBOSE,
    )
    _re_exec_close = re.compile(
        r"""            # Multi-line exec end
            \s*         # Can start with any number of spaces
            \+@         # Match the block close tag "-@"
            \s*$        # Any extra spaces matched after tag
            ()          # Empty capture (so same capture group as eval)
        """,
        re.VERBOSE,
    )
    _re_eval_one_line = re.compile(
        r"""            # Eval with open/close tag on single line
            (.*)        # Capture all text before eval open tag
            @%          # Match the eval open tag "@%"
            (.+)        # Capture the expression to eval
            %@          # Match the eval close tag "%@"
            (.*)        # Capture the rest of the line
        """,
        re.VERBOSE,
    )
    _re_eval_open = re.compile(
        r"""            # Multi-line eval start
            (.*)        # Capture all text before eval open tag
            @\%         # Match the eval open tag "@%"
            (.+)        # Capture the expression to eval
        """,
        re.VERBOSE,
    )
    _re_eval_close = re.compile(
        r"""            # Multi-line eval end
            (.*)        # Capture all text before eval close tag
            \%@         # Match the eval close tag "%@"; must be last thing on line
            \s*$        # Any extra spaces after close tag
        """,
        re.VERBOSE,
    )
    _re_include = re.compile(
        r"""
            (.*)        # Capture all text before include tag
            @@include   # Match the include start
            \s+         # Match at least one space between include and filename
            (\S+?)      # Capture filename; non-greedy; no spaces allowed in fname
            @@          # Match the include end tag
            \s*$        # Any extra spaces after close tag
        """,
        re.VERBOSE,
    )
    _re_comment = re.compile(r"\s*#")

    def __init__(self, stream):
        self._streams = [stream]
        self._macro_globals = {}
        self._lines = ""
        self.last_error = None
        self._parsers = [
            self._parse_comment,
            self._parse_include,
            self._parse_exec,
            self._parse_eval,
        ]

    def load(self):
        """Load YAML with embedded Python code."""
        self._lines = self._process_stream()
        return self._lines

    def dump(self):
        """Dump processed YAML checking that it's properly formmatted YAML."""
        try:
            return yaml.dump(yaml.safe_load(self._lines))
        except yaml.YAMLError as exc:
            if hasattr(exc, "problem_mark"):
                mark = exc.problem_mark
                self.last_error = exc
                LOG.exception(exc)
                lines = self._lines.split("\n")
                for i in range(max(mark.line - 5, 0), min(mark.line + 5, len(lines))):
                    LOG.error(f"{i+1: 4} {lines[i]}")
            return ""

    def _process_stream(self, indent_str=""):
        try:
            tokens = [self._parse_line(line) for line in self._streams[-1]]
            # for token in tokens:
            #     LOG.error(token)
            if indent_str:
                self._indent_tokens(tokens, indent_str)
            output = [self._process_line(token).rstrip(" \t") for token in tokens]
            return "".join(output)
        except Exception as exc:
            LOG.exception(exc)
            self.last_error = exc
            return ""

    def _process_line(self, token):
        line_type = token[0]
        if line_type == LineType.REGULAR:
            return f"{token[1]}{token[2]}"
        if line_type == LineType.COMMENT:
            return token[2]
        if line_type == LineType.EXEC:
            exec(textwrap.dedent(token[2]), self._macro_globals)
            return token[1]
        if line_type == LineType.EVAL:
            return self._process_eval(token)
        if line_type == LineType.INCLUDE:
            return self._process_include(token)
        return ""

    def _process_eval(self, token):
        evaled = eval(token[2], self._macro_globals)
        if isinstance(evaled, str):
            if "\n" in evaled:
                indent_string = "\n" + " " * len(token[1])
                evaled = evaled.replace("\n", indent_string)
        else:
            evaled = evaled.__repr__()
        return f"{token[1]}{evaled}{token[3]}\n"

    def _process_include(self, token):
        indent_string = " " * len(token[1])
        filename = token[2]
        with open(filename) as stream:
            self._streams.append(stream)
            lines = self._process_stream(indent_string)
        return f"{token[1]}{lines}\n"

    def _indent_tokens(self, tokens, indent_str):
        first_line = True
        for idx, token in enumerate(tokens):
            if token[0] in [
                LineType.COMMENT,
                LineType.INCLUDE,
                LineType.EXEC,
            ]:
                continue
            if first_line:
                # Don't indent the first line
                first_line = False
                continue
            tokens[idx] = Token(token[0], f"{indent_str}{token[1]}", token[2], token[3])

    def _parse_line(self, line):
        for parser in self._parsers:
            parser_return_value = parser(line)
            if parser_return_value:
                return parser_return_value
        return Token(LineType.REGULAR, "", line, None)

    def _parse_comment(self, line):
        if self._re_comment.match(line):
            return Token(LineType.COMMENT, "", line, "")
        return None

    def _parse_include(self, line):
        match = self._re_include.match(line)
        if match:
            return Token(LineType.INCLUDE, match.group(1), match.group(2), "")
        return None

    def _capture_block(self, opening_match, closing_re, capture_type):
        return_text = opening_match.group(1)
        block_lines = opening_match.group(2)
        for line in self._streams[-1]:
            match = closing_re.match(line)
            if match:
                block_lines += match.group(1)
                return Token(capture_type, return_text, block_lines, "")
            block_lines += line

        # Error: block end not found before end of file
        return None

    def _parse_eval(self, line):
        match = self._re_eval_one_line.match(line)
        if match:
            return Token(LineType.EVAL, match.group(1), match.group(2), match.group(3))

        match = self._re_eval_open.match(line)
        if match:
            return self._capture_block(match, self._re_eval_close, LineType.EVAL)

        return None

    def _parse_exec(self, line):
        match = self._re_exec_one_line.match(line)
        if match:
            return Token(LineType.EXEC, "", match.group(1), "")

        match = self._re_exec_open.match(line)
        if match:
            return self._capture_block(match, self._re_exec_close, LineType.EXEC)

        return None
