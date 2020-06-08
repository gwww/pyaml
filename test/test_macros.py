import pytest
import yaml
from textwrap import dedent

from yaml_macros.macros import yaml_macros


def test_eval_dict():
    parsed = yaml_macros(
        ("@@from macros import resources@@\n" "resources:\n" "  @@resources()@@\n")
    )
    assert parsed == ("resources:\n" "- type: module\n" "  url: foo\n")
    assert yaml.safe_load(parsed) == {"resources": [{"type": "module", "url": "foo"}]}


def test_eval_single_line_string():
    parsed = yaml_macros(
        (
            "@@\n"
            "some_variable = 'yipee!'\n"
            "@@\n"
            "yaml_stuff:\n"
            "  foo: @@some_variable@@\n"
        )
    )
    assert yaml.safe_load(parsed) == {"yaml_stuff": {"foo": "yipee!"}}


def test_eval_multiple_line_string():
    parsed = yaml_macros(
        (
            "@@\n"
            "some_var = '- type: module\\n  url: foo'\n"
            "@@\n"
            "stuff:\n"
            "  @@some_var@@\n"
        )
    )
    assert yaml.safe_load(parsed) == {"stuff": [{"type": "module", "url": "foo"}]}


def test_exec_function():
    parsed = yaml_macros(
        (
            "@@\n"
            "def some_function(arg):\n"
            "    return f'foo: Hello {arg}!'\n"
            "@@\n"
            "stuff:\n"
            "  @@some_function('world')@@\n"
        )
    )
    assert yaml.safe_load(parsed) == {"stuff": {"foo": "Hello world!"}}
