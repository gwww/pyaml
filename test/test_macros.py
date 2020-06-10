import pytest
import yaml
from textwrap import dedent
import unittest.mock as mock

from yaml_macros.macros import yaml_macros


def test_eval_dict():
    parsed = yaml_macros(
        ("         @@from macros import resources@@\n" "resources:\n" "  @@resources()@@\n")
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


def test_import_does_not_exist():
    with pytest.raises(ModuleNotFoundError):
        parsed = yaml_macros(("@@import some_thing_that_does_not_exist@@\n"))


def test_exec_empty_block():
    parsed = yaml_macros(
        (
            "@@\n"
            "@@\n"
            "stuff:\n"
            "  cow: goes_moo\n"
        )
    )
    assert yaml.safe_load(parsed) == {"stuff": {"cow": "goes_moo"}}

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


def test_include():
    with mock.patch("builtins.open", mock.mock_open(read_data="foo: Hello world!")):
        parsed = yaml_macros(
            (
                "stuff:\n"
                "  - @@include include.yaml@@\n"
                "  - @@include include.yaml@@\n"
            )
        )
    assert yaml.safe_load(parsed) == {
        "stuff": [{"foo": "Hello world!"}, {"foo": "Hello world!"}]
    }


def test_include_file_does_not_exist():
    with pytest.raises(FileNotFoundError):
        parsed = yaml_macros(
            ("stuff:\n" "  @@include some_name_that_does_not_exist.oh_gosh@@\n")
        )
