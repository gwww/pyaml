# YAML Macros

Library for adding macro like functionality to YAML

https://github.com/gwww/yaml-macros

## Requirements

- Python 3.6 (or higher)

## Description

Docs are light at this point. Take a look a `example/test.yaml` and associated
files and at `test/test_macros.py`.

This lib is distinguished from other generic templating languages in that
indentation, crucial in YAML, is preserved on `include`, `eval`, etc.

This uses python's `eval` and `exec` functions. Read about security concerns
about use of those. Since this software is not accessing unaudited code the risk
of `eval` and `exec` is viewed as low. Never accept/use python "macros" without
inspecting the code.

## Installation

Note: pip version coming soon.

```bash
    $ pip install yaml_macros
```

## Overview

## Development

This project uses [poetry](https://poetry.eustace.io/) for development dependencies. Installation instructions are on their website.

To get started developing:

```
git clone https://github.com/gwww/yaml-macros.git
cd yaml-macros
poetry install
poetry shell # Or activate the created virtual environment
make test # to ensure everything installed properly
```

There is a `Makefile` in the root directory as well. The `make` command
followed by one of the targets in the `Makefile` can be used. If you don't
have or wish to use `make` the `Makefile` serves as examples of common
commands that can be run.
