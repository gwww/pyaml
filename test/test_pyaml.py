import unittest.mock as mock
from textwrap import dedent

import pytest
import yaml

from pyaml import pyaml_string


def test_simple_one_line_eval():
    (parsed, error) = pyaml_string(("yaml_stuff:\n" "  foo: @%42%@\n"))
    assert yaml.safe_load(parsed) == {"yaml_stuff": {"foo": 42}}


def test_simple_one_line_eval_returns_string():
    (parsed, error) = pyaml_string(("yaml_stuff:\n" "  foo: @%'42'%@\n"))
    assert yaml.safe_load(parsed) == {"yaml_stuff": {"foo": 42}}


def test_simple_one_line_eval_with_extra_characters():
    (parsed, error) = pyaml_string(("yaml_stuff:\n" "  foo: @%42%@42\n"))
    assert yaml.safe_load(parsed) == {"yaml_stuff": {"foo": 4242}}


def test_one_line_eval_non_string_return():
    (parsed, error) = pyaml_string(("yaml_stuff:\n" "  @%{'foo': 42}%@\n"))
    assert yaml.safe_load(parsed) == {"yaml_stuff": {"foo": 42}}


def test_simple_multiline_eval():
    (parsed, error) = pyaml_string(
        ("yaml_stuff:\n" "  foo: @%'''\n" "    Some text!\n" "'''%@\n")
    )
    assert yaml.safe_load(parsed) == {"yaml_stuff": {"foo": "Some text!"}}


def test_simple_exec_block():
    (parsed, error) = pyaml_string(
        (
            "@+\n"
            "some_variable = 'yipee!'\n"
            "+@\n"
            "yaml_stuff:\n"
            "  foo: @%some_variable%@\n"
        )
    )
    assert yaml.safe_load(parsed) == {"yaml_stuff": {"foo": "yipee!"}}


def test_eval_multiple_line_string():
    (parsed, error) = pyaml_string(
        (
            "@+\n"
            "some_var = '- type: module\\n  url: foo'\n"
            "+@\n"
            "stuff:\n"
            "  @%some_var%@\n"
        )
    )
    assert yaml.safe_load(parsed) == {"stuff": [{"type": "module", "url": "foo"}]}


def test_exec_single_line():
    (parsed, error) = pyaml_string(
        ("@+some_var = 42+@\n" "yaml_stuff:\n" "  foo: @%some_var%@\n")
    )
    assert yaml.safe_load(parsed) == {"yaml_stuff": {"foo": 42}}


def test_import_and_eval_dict():
    (parsed, error) = pyaml_string(
        (
            "@+from import_test_code import resources+@\n"
            "resources:\n"
            "  @%resources()%@\n"
        )
    )
    assert parsed == ("resources:\n" "- type: module\n" "  url: foo\n")
    assert yaml.safe_load(parsed) == {"resources": [{"type": "module", "url": "foo"}]}


def test_exec_empty_block():
    (parsed, error) = pyaml_string(("@+\n" "+@\n" "stuff:\n" "  cow: goes_moo\n"))
    assert yaml.safe_load(parsed) == {"stuff": {"cow": "goes_moo"}}


def test_exec_function():
    (parsed, error) = pyaml_string(
        (
            "@+\n"
            "def some_function(arg):\n"
            "    return f'foo: Hello {arg}!'\n"
            "+@\n"
            "stuff:\n"
            "  @%some_function('world')%@\n"
        )
    )
    assert yaml.safe_load(parsed) == {"stuff": {"foo": "Hello world!"}}


def test_exec_indented_block_gets_dedented():
    (parsed, error) = pyaml_string(
        (
            "@+\n"
            "    def some_function(arg):\n"
            "        return f'foo: Hello {arg}!'\n"
            "+@\n"
            "stuff:\n"
            "  @%some_function('world')%@\n"
        )
    )
    assert yaml.safe_load(parsed) == {"stuff": {"foo": "Hello world!"}}


def test_include():
    with mock.patch("builtins.open", mock.mock_open(read_data="foo: Hello world!")):
        (parsed, error) = pyaml_string(
            (
                "stuff:\n"
                "  - @@include include.yaml@@\n"
                "  - @@include include.yaml@@\n"
            )
        )
    assert yaml.safe_load(parsed) == {
        "stuff": [{"foo": "Hello world!"}, {"foo": "Hello world!"}]
    }


def test_include_that_has_variable():
    with mock.patch(
        "builtins.open", mock.mock_open(read_data="@+\nvar=42\n+@\n@%var%@\n")
    ):
        (parsed, error) = pyaml_string(
            ("stuff:\n" "  everything: @@include include.yaml@@\n")
        )
    assert yaml.safe_load(parsed) == {
        "stuff": {"everything": 42},
    }


def test_exec_include_inline_block():
    with mock.patch(
        "builtins.open",
        mock.mock_open(read_data=("@+\n" "some_var=42\n" "+@\n" "@%some_var%@\n")),
    ):
        (parsed, error) = pyaml_string(
            (
                "stuffy_mc_stuff_face:\n"
                "  - @@include included_file_that_is_mocked_out.yaml@@\n"
                "  - @@include included_file_that_is_mocked_out.yaml@@\n"
            )
        )
    assert yaml.safe_load(parsed) == {"stuffy_mc_stuff_face": [42, 42]}


def test_exec_include_inline_block_with_eval():
    with mock.patch(
        "builtins.open",
        mock.mock_open(
            read_data=(
                "@+\n"
                "some_variable='jersey cow'\n"
                "+@\n"
                "zoo: bar\n"
                "moo: @%some_variable%@\n"
            )
        ),
    ):
        (parsed, error) = pyaml_string(
            ("some_yaml:\n" "  - @@include included_file_mocked_out.yaml@@\n")
        )
    assert yaml.safe_load(parsed) == {
        "some_yaml": [{"zoo": "bar", "moo": "jersey cow"}]
    }
