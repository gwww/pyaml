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
import yaml

from collections import namedtuple
from enum import Enum

from .capture import CaptureOutput


LOG = logging.getLogger(__name__)

LineType = Enum("LineType", "REGULAR COMMENT EXEC EVAL")
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
    processor = Pyaml()
    lines = processor.load(stream)
    lines = re.sub(r"\n\s+\n", "\n", lines)
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
            (.*)           # Capture all text before include tag
            @@\s?include   # Match the include start
            \s+            # Match at least one space between include and filename
            (\S+?)         # Capture filename; no spaces allowed in fname
            @@             # Match the include end tag
            \s*$           # Any extra spaces after close tag
        """,
        re.VERBOSE,
    )
    _re_comment = re.compile(r"\s*#")

    def __init__(self):
        self._streams = []
        self._macro_globals = {}
        self._lines = ""
        self.last_error = None
        self._parsers = [
            self._parse_comment,
            self._parse_include,
            self._parse_exec,
            self._parse_eval,
        ]

    def load(self, stream):
        """Load YAML with embedded Python code."""
        self._lines = self._process(stream)
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

    def _process(self, stream):
        try:
            tokens = self._parse_stream(stream)
            # for token in tokens:
            #     LOG.error(token)
            output = self._process_tokens(tokens)
            return "".join(output)
        except Exception as exc:
            LOG.exception(exc)
            self.last_error = exc
            return ""

    def _parse_stream(self, stream):
        tokens = []
        self._streams.append(stream)
        for line in self._streams[-1]:
            result = self._parse_line(line)
            if isinstance(result, list):
                tokens.extend(result)
            else:
                tokens.append(result)
        self._streams.pop()
        return tokens

    def _process_tokens(self, tokens):
        output = [self._process_token(token) for token in tokens]
        return output

    def _process_token(self, token):
        line_type = token[0]
        if line_type in [LineType.REGULAR, LineType.COMMENT]:
            return f"{token[1]}{token[2]}"
        if line_type == LineType.EXEC:
            exec(textwrap.dedent(token[2]), self._macro_globals)
            return token[1]
        if line_type == LineType.EVAL:
            return self._process_eval(token)
        return ""

    def _process_eval(self, token):
        with CaptureOutput() as output:
            evaled = eval(token[2], self._macro_globals)

        if evaled == None:
            evaled = ""

        if not isinstance(evaled, str):
            evaled = evaled.__repr__()

        if output:
            evaled = f"{output._stringio.getvalue()}{evaled}"

        indent_string = "\n" + " " * len(token[1])
        evaled = evaled.replace("\n", indent_string)

        return f"{token[1]}{evaled}{token[3]}\n"

    def _parse_line(self, line):
        for parser in self._parsers:
            parser_return_value = parser(line)
            if parser_return_value is not None:
                return parser_return_value
        return Token(LineType.REGULAR, "", line, None)

    def _parse_comment(self, line):
        if self._re_comment.match(line):
            return Token(LineType.COMMENT, "", line, "")
        return None

    def _parse_include(self, line):
        match = self._re_include.match(line)
        if match:
            prefix = match.group(1)
            indent_string = " " * len(prefix)
            filename = match.group(2)
            with open(filename) as stream:
                tokens = self._parse_stream(stream)
                self._indent_tokens(tokens, prefix, indent_string)
                return tokens
            return []
        return None

    def _indent_tokens(self, tokens, prefix, indent_string):
        for idx, token in enumerate(tokens):
            if token[0] == LineType.EXEC:
                continue
            tokens[idx] = Token(token[0], f"{prefix}{token[1]}", token[2], token[3])
            prefix = indent_string

    def _grab_block(self, opening_match, closing_re, capture_type):
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
            return self._grab_block(match, self._re_eval_close, LineType.EVAL)

        return None

    def _parse_exec(self, line):
        match = self._re_exec_one_line.match(line)
        if match:
            return Token(LineType.EXEC, "", match.group(1), "")

        match = self._re_exec_open.match(line)
        if match:
            return self._grab_block(match, self._re_exec_close, LineType.EXEC)

        return None
