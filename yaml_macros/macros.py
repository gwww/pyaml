"""
Entry point for parsing YAML and picking out the Python
'macros' for expanding.
"""

import io
import re
import textwrap
import yaml


def yaml_macros_file(filename, reformat=True):
    """Convert macros in YAML file to pure YAML."""
    with open(filename) as io_handle:
        return _yaml_macros(stream, reformat)


def yaml_macros_string(yaml_str, reformat=True):
    """Convert macros in YAML string to pure YAML."""
    with io.StringIO(yaml_str) as stream:
        return _yaml_macros(stream, reformat)


def _yaml_macros(stream, reformat):
    processor = YAML_macros(stream)
    lines = processor.load()
    if reformat:
        return processor.dump()
    return lines


class YAML_macros:
    _re_exec_block1 = re.compile(r"^(.*)@@\s*$")
    _re_exec_block2 = re.compile(r"^\s*@@\s*$")
    _re_import = re.compile(r"^\s*@@((import|from)\s+.*?)(@@)?\s*$")
    _re_comment = re.compile(r"^\s*#")
    _re_include = re.compile(r"^(.*)@@include\s+(\S+?)(@@)?\s*$")
    _re_eval1 = re.compile(r"^(.*)@@(.+)@@(.*)")
    _re_eval2 = re.compile(r"^(.*)@@(.+)()")

    def __init__(self, stream):
        self._stream = [stream]
        self._parsing_block = False
        self._block_lines = ""
        self._macro_globals = {}

    def load(self):
        self._lines = self._process_stream()
        return self._lines

    def dump(self):
        return yaml.dump(yaml.safe_load(self._lines))

    def _process_stream(self):
        lines = []
        for line in self._stream[-1]:
            line = self._parse_line(line)
            if not line:
                continue
            lines.append(line)
        self._stream.pop()
        return "".join(lines)

    def _parse_line(self, line):
        if not self._parsing_block and self._parse_comment(line):
            return line
        (parsed, prefix) = self._parse_exec_block(line)
        if parsed:
            return prefix
        if self._parse_import(line):
            return None
        lines = self._parse_include(line)
        if lines:
            return lines
        eval_line = self._parse_eval(line)
        if eval_line:
            return eval_line

        return line

    def _parse_exec_block(self, line):
        if not self._parsing_block:
            if line.count("@@") == 1:
                match = self._re_exec_block1.match(line)
                if match:
                    self._parsing_block = True
                    self._block_lines = ""
                    return (True, match.group(1))
            return (False, None)
        else:
            match = self._re_exec_block2.match(line)
            if match:
                self._parsing_block = False
                exec(textwrap.dedent(self._block_lines), self._macro_globals)
                self._block_lines = ""
            else:
                self._block_lines += line
            return (True, None)

    def _parse_import(self, line):
        match = self._re_import.match(line)
        if not match:
            return False

        exec(match.group(1), self._macro_globals)
        return True

    def _parse_comment(self, line):
        return not self._re_comment.match(line) is None

    def _parse_include(self, line):
        lines = None
        match = self._re_include.match(line)
        if match:
            indent_string = "\n" + " " * len(match.group(1))
            filename = match.group(2)
            with open(filename) as file:
                include_string = (
                    match.group(1) + file.read().replace("\n", indent_string) + "\n"
                )
            with io.StringIO(include_string) as stream:
                self._stream.append(stream)
                lines = self._process_stream()
        return lines


    def _parse_eval(self, line):
        match = self._re_eval1.match(line) or self._re_eval2.match(line)
        if not match:
            return None

        evaled = eval(match.group(2), self._macro_globals)
        if isinstance(evaled, str):
            if "\n" in evaled:
                indent_string = "\n" + " " * len(match.group(1))
                evaled = evaled.replace("\n", indent_string)
        else:
            evaled = evaled.__repr__()

        return f"{match.group(1)}{evaled}{match.group(3)}\n"
