"""
Entry point for parsing YAML and picking out the Python
'macros' for expanding
"""

import re
import yaml

_macro_globals = {}


def yaml_macros_file(file, reformat=True):
    """Convert macros in YAML file to pure YAML."""
    with open(file) as file_handle:
        lines = [_parse_line(line) for line in file_handle]
    return _yaml_return(lines, reformat)


def yaml_macros(yaml_str, reformat=True):
    """Convert macros in YAML string to pure YAML."""
    lines = [_parse_line(line) for line in yaml_str.splitlines(True)]
    return _yaml_return(lines, reformat)


def _yaml_return(lines, reformat):
    if reformat:
        data = yaml.safe_load("".join(lines))
        return yaml.dump(data)

    return "".join(lines)


def _parse_line(line):
    if _parse_exec_block(line):
        return ""
    if _parse_import(line):
        return ""
    return(_parse_eval(line))


def _parse_import(line):
    match = re.match(r"^@@((import|from)\s+.*)@@\s*$", line)
    if not match:
        return False

    exec(match.group(1), _macro_globals)
    return True


def _parse_eval(line):
    match = re.match(r"^(.*)@@(.+)@@(.*)", line)
    if not match:
        return line

    evaled = eval(match.group(2), _macro_globals)
    if isinstance(evaled, str):
        if "\n" in evaled:
            prefix_str = "\n" + " " * len(match.group(1))
            evaled = re.sub(r"\n", prefix_str, evaled)
    else:
        evaled = evaled.__repr__()

    return f"{match.group(1)}{evaled}{match.group(3)}"


def _parse_exec_block(line):
    match = re.match(r"^@@\s*$", line)
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
