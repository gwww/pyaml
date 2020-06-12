"""
Entry point for parsing YAML and picking out the Python
'macros' for expanding.
"""

import io
import re
import textwrap
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
    lines = []
    for line in io_handle:
        line = _parse_line(line)
        if not line:
            continue
        lines.append(line)
    return "".join(lines)


def _parse_line(line):
    if not _parse_exec_block.parsing and _parse_comment(line):
        return line
    (parsed, prefix) = _parse_exec_block(line)
    if parsed:
        return prefix
    if _parse_import(line):
        return None
    lines = _parse_include(line)
    if lines:
        return lines
    eval_line = _parse_eval(line)
    if eval_line:
        return eval_line

    return line


_re_exec_block1 = re.compile(r"^(.*)@@\s*$")
_re_exec_block2 = re.compile(r"^\s*@@\s*$")


def _parse_exec_block(line):
    if not _parse_exec_block.parsing:
        if line.count("@@") == 1:
            match = _re_exec_block1.match(line)
            if match:
                _parse_exec_block.parsing = True
                _parse_exec_block.lines = ""
                return (True, match.group(1))
        return (False, None)
    else:
        match = _re_exec_block2.match(line)
        if match:
            _parse_exec_block.parsing = False
            exec(textwrap.dedent(_parse_exec_block.lines), _macro_globals)
            _parse_exec_block.lines = ""
        else:
            _parse_exec_block.lines += line
        return (True, None)


_parse_exec_block.parsing = False
_parse_exec_block.lines = ""


_re_import = re.compile(r"^\s*@@((import|from)\s+.*?)(@@)?\s*$")


def _parse_import(line):
    match = _re_import.match(line)
    if not match:
        return False

    exec(match.group(1), _macro_globals)
    return True


_re_comment = re.compile(r"^\s*#")


def _parse_comment(line):
    return not _re_comment.match(line) is None


_re_include = re.compile(r"^(.*)@@include\s+(\S+?)(@@)?\s*$")


def _parse_include(line):
    lines = None
    match = _re_include.match(line)
    if match:
        indent_string = "\n" + " " * len(match.group(1))
        filename = match.group(2)
        with open(filename) as file:
            include_string = (
                match.group(1) + file.read().replace("\n", indent_string) + "\n"
            )
        with io.StringIO(include_string) as io_handle:
            breakpoint()
            lines = _read_lines(io_handle)
    return lines


_re_eval1 = re.compile(r"^(.*)@@(.+)@@(.*)")
_re_eval2 = re.compile(r"^(.*)@@(.+)()")


def _parse_eval(line):
    match = _re_eval1.match(line) or _re_eval2.match(line)
    if not match:
        return None

    evaled = eval(match.group(2), _macro_globals)
    if isinstance(evaled, str):
        if "\n" in evaled:
            indent_string = "\n" + " " * len(match.group(1))
            evaled = evaled.replace("\n", indent_string)
    else:
        evaled = evaled.__repr__()

    return f"{match.group(1)}{evaled}{match.group(3)}\n"
