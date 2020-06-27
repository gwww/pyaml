# Python YAML

Library for adding Python code in YAML processing

https://github.com/gwww/pyaml

## Requirements

- Python 3.6 (or higher)

## Description

Docs are light at this point. Take a look a `example/test.yaml` and associated
files and at `test/test_pyaml.py`.

This lib is distinguished from other templating languages in that
indentation, crucial in YAML, is preserved on `include`, `eval`, and `exec`

This uses python's `eval` and `exec` functions. Read about security concerns
about use of those. Since this software is not accessing "unaudited" code the
security risk of using `eval` and `exec` is viewed as low. Never accept/use
Python code without inspecting the code.

## Installation

```bash
    $ pip install pyaml
```

## Overview

`pyaml` reads a YAML file and runs the tagged code inside the YAML file. It 
supports three processing tags: `eval` to run code, `exec` to load code, and `include` to include other files in the context of the current file. All three
processors are aware of YAML indenting requirements.

### Eval

`eval` is triggered in a YAML file using the tags `@%` to open an `eval` and `%@`
to close an `eval`. Anything in between the two tags is passed to the Python `eval`
function for processing. Whatever is returned from the `eval` is inserted into
the YAML stream. The starting character position of the opening tag is used as
the indent level prepended to everything returned.

For the examples in this section assume that the following Python code
is in the module `resources.py` and that file contains the following:
```
from random import randrange

_PATH = "/local/cards/"

def resources(module, module_type):
    version = f"?v={randrange(1000000)}"
    # This works to, the lib can handle lists, dicts, etc as return values:
    # return [{'url': f"{_PATH}/{module}{version}", "type": module_type}]
    return f"url: {_PATH}/{module}{version}\ntype: {module_type}"
```

Example 1:
```
@+ from resources import resources +@
resources:
  - @% resources("layout-card", "module") %@
  - @% resources("card-mod", "module") %@
```

Processing with `pyaml` results in:
```
resources:
  - url: /local/cards//layout-card?v=238120
    type: module
  - url: /local/cards//card-mod?v=885753
    type: module
```

Notice that the indentation is preserved from the position on the line where
the `eval` was invoked.

Note that the space around the start and end tags is optional.

### Exec

`exec` is triggered in a YAML file using the tags `@%` to open an `eval` and `%@`
to close an `exec`. Anything in between the two tags is passed to the Python `exec`
function for processing. Whatever is returned from the `exec` is NOT inserted into
the YAML stream. The code inside the `exec` tags is `dedent`ed meaning 
common leading whitespace on each line is removed.

Example 2:
```
@+
def markdown_card(label):
    return \
f"""type: markdown
style: |
  ha-card {{background: purple}}
content: |
  ## {label}"""
+@

title: My awesome Lovelace config
views:
  - title: Home
    cards:
      - @%markdown_card("Kitchen")%@
      - @%markdown_card("Living room")%@
```

Processing with `pyaml` results in:
```
title: My awesome Lovelace config
views:
  - title: Home
    cards:
      - type: markdown
        style: |
          ha-card {background: purple}
        content: |
          ## Kitchen
      - type: markdown
        style: |
          ha-card {background: purple}
        content: |
          ## Living room
```

Note: any type of Python code may exist between the tags, however,
it is likely more maintainable to put code, such the code in the
example above, into it's own Python module.

### Include

Includes the contents of the file into the YAML stream. The included file
may contain `eval` and `exec` blocks. Include is trigged using the same
open and closing tag of `@@`.

The advantage of using `pyaml` include over the include processing from PyYAML
is that `pyaml` preserves indentation.

For example if `example3_include.yaml` contains:
```
- zoo: tiger
- moo: cow
```

And the following YAML file:
```
big_pets:
  @@include some_file.yaml@@
```

Processing with `pyaml` results in:
```
big_pets:
  - zoo: tiger
  - moo: cow
```

## Development

This project uses [poetry](https://poetry.eustace.io/) for development dependencies. Installation instructions are on their website.

To get started developing:

```
git clone https://github.com/gwww/pyaml.git
cd pyaml
poetry install
poetry shell # Or activate the created virtual environment
pytest # to ensure everything installed properly
```

There is a `Makefile` in the root directory as well. The `make` command
followed by one of the targets in the `Makefile` can be used. If you don't
have or wish to use `make` the `Makefile` serves as examples of common
commands that can be run.
