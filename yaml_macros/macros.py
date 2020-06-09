"""
Entry point for parsing YAML and picking out the Python
'macros' for expanding.
"""

import io
import re
import yaml

_macro_globals = {}


def yaml_macros_file(filename, reformat=True):
    """Convert macros in YAML file to pure YAML."""
    with open(filename) as io_handle:
        lines = _process_file(io_handle, reformat)
    return lines


def yaml_macros(yaml_str, reformat=True):
    """Convert macros in YAML string to pure YAML."""
    with io.StringIO(yaml_str) as io_handle:
        lines = _process_file(io_handle, reformat)
    return lines


def _process_file(io_handle, reformat):
    lines = _read_lines(io_handle)
    if reformat:
        data = yaml.safe_load(lines)
        return yaml.dump(data)
    return lines


def _read_lines(io_handle):
    return "".join([_parse_line(line) for line in io_handle])


_re_exec_block = re.compile(r"^@@\s*$")
_re_import = re.compile(r"^@@((import|from)\s+.*)@@\s*$")
_re_comment = re.compile(r"^\s*#")
_re_include = re.compile(r"^(.*)@@include\s+(\S+)@@\s*$")
_re_eval = re.compile(r"^(.*)@@(.+)@@(.*)")


def _parse_line(line):
    if _parse_exec_block(line):
        return ""
    if _parse_import(line):
        return ""
    if _parse_comment(line):
        return line
    lines = _parse_include(line)
    if lines:
        return lines
    return _parse_eval(line)


def _parse_exec_block(line):
    match = _re_exec_block.match(line)
    if not _parse_exec_block.parsing:
        if match:
            _parse_exec_block.parsing = True
            _parse_exec_block.lines = ""
        return _parse_exec_block.parsing
    else:
        if match:
            _parse_exec_block.parsing = False
            exec(_parse_exec_block.lines, _macro_globals)
            _parse_exec_block.lines = ""
        else:
            _parse_exec_block.lines += line
        return True


_parse_exec_block.parsing = False
_parse_exec_block.lines = ""


def _parse_import(line):
    match = _re_import.match(line)
    if not match:
        return False

    exec(match.group(1), _macro_globals)
    return True


def _parse_comment(line):
    return not _re_comment.match(line) is None


def _parse_include(line):
    lines = None
    match = _re_include.match(line)
    if match:
        indent_str = "\n" + " " * len(match.group(1))
        filename = match.group(2)
        with open(filename) as file:
            include_str = match.group(1) + file.read().replace("\n", indent_str) + "\n"
        with io.StringIO(include_str) as io_handle:
            lines = _read_lines(io_handle)
    return lines


def _parse_eval(line):
    match = _re_eval.match(line)
    if not match:
        return line

    evaled = eval(match.group(2), _macro_globals)
    if isinstance(evaled, str):
        if "\n" in evaled:
            indent_str = "\n" + " " * len(match.group(1))
            evaled = evaled.replace("\n", indent_str)
    else:
        evaled = evaled.__repr__()

    return f"{match.group(1)}{evaled}{match.group(3)}\n"
