import pytest
import yaml
from textwrap import dedent
import unittest.mock as mock

from yaml_macros.macros import yaml_macros_string


def test_simplest_macro():
    parsed = yaml_macros_string(("yaml_stuff:\n" "  foo: @@42@@\n"))
    assert yaml.safe_load(parsed) == {"yaml_stuff": {"foo": 42}}


def test_eval_single_line_string():
    parsed = yaml_macros_string(
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
    parsed = yaml_macros_string(
        (
            "@@\n"
            "some_var = '- type: module\\n  url: foo'\n"
            "@@\n"
            "stuff:\n"
            "  @@some_var@@\n"
        )
    )
    assert yaml.safe_load(parsed) == {"stuff": [{"type": "module", "url": "foo"}]}


def test_import_and_eval_dict():
    parsed = yaml_macros_string(
        ("@@from macros import resources@@\n" "resources:\n" "  @@resources()@@\n")
    )
    assert parsed == ("resources:\n" "- type: module\n" "  url: foo\n")
    assert yaml.safe_load(parsed) == {"resources": [{"type": "module", "url": "foo"}]}


def test_import_does_not_exist():
    with pytest.raises(ModuleNotFoundError):
        parsed = yaml_macros_string(("@@import some_thing_that_does_not_exist@@\n"))


def test_exec_empty_block():
    parsed = yaml_macros_string(("@@\n" "@@\n" "stuff:\n" "  cow: goes_moo\n"))
    assert yaml.safe_load(parsed) == {"stuff": {"cow": "goes_moo"}}


def test_exec_function():
    parsed = yaml_macros_string(
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


def test_exec_indented_block_gets_dedented():
    parsed = yaml_macros_string(
        (
            "@@\n"
            "    def some_function(arg):\n"
            "        return f'foo: Hello {arg}!'\n"
            "@@\n"
            "stuff:\n"
            "  @@some_function('world')@@\n"
        )
    )
    assert yaml.safe_load(parsed) == {"stuff": {"foo": "Hello world!"}}


def test_include_file_does_not_exist():
    with pytest.raises(FileNotFoundError):
        parsed = yaml_macros_string(
            ("stuff:\n" "  @@include some_name_that_does_not_exist.oh_gosh@@\n")
        )


def test_include():
    with mock.patch("builtins.open", mock.mock_open(read_data="foo: Hello world!")):
        parsed = yaml_macros_string(
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
        "builtins.open", mock.mock_open(read_data="@@\nvar=42\n@@\n@@var@@\n")
    ):
        parsed = yaml_macros_string(
            ("stuff:\n" "  everything: @@include include.yaml@@\n")
        )
    assert yaml.safe_load(parsed) == {
        "stuff": {"everything": 42},
    }


def test_include_opening_marker_only():
    with mock.patch("builtins.open", mock.mock_open(read_data="foo: Hello world!")):
        parsed = yaml_macros_string(("stuff:\n" "  - @@include include.yaml\n"))
    assert yaml.safe_load(parsed) == {"stuff": [{"foo": "Hello world!"}]}


def test_import_opening_marker_only():
    parsed = yaml_macros_string(
        ("@@from macros import resources\n" "resources:\n" "  @@resources()@@\n")
    )
    assert parsed == ("resources:\n" "- type: module\n" "  url: foo\n")
    assert yaml.safe_load(parsed) == {"resources": [{"type": "module", "url": "foo"}]}


def test_eval_opening_marker_only():
    parsed = yaml_macros_string(
        (
            "@@\n"
            "some_variable = 'yipee!'\n"
            "@@\n"
            "yaml_stuff:\n"
            "  foo: @@some_variable\n"
        )
    )
    assert yaml.safe_load(parsed) == {"yaml_stuff": {"foo": "yipee!"}}


def test_exec_inline_block():
    parsed = yaml_macros_string(("stuff:\n" "  - @@\n" "   x=42\n" "@@\n" "@@x@@\n"))
    assert yaml.safe_load(parsed) == {"stuff": [42]}


def test_exec_include_inline_block():
    with mock.patch(
        "builtins.open",
        mock.mock_open(read_data=("@@\n" "some_var=42\n" "@@\n" "@@some_var\n")),
    ):
        parsed = yaml_macros_string(
            (
                "stuffy_mc_stuff_face:\n"
                "  - @@include included_file_that_is_mocked_out.yaml\n"
                "  - @@include included_file_that_is_mocked_out.yaml\n"
            )
        )
    assert yaml.safe_load(parsed) == {"stuffy_mc_stuff_face": [42, 42]}


def test_exec_include_inline_block_with_eval():
    with mock.patch(
        "builtins.open",
        mock.mock_open(
            read_data=(
                "@@\n"
                "some_variable='jersey cow'\n"
                "@@\n"
                "zoo: bar\n"
                "moo: @@some_variable@@\n"
            )
        ),
    ):
        parsed = yaml_macros_string(
            ("some_yaml:\n" "  - @@include included_file_that_is_mocked_out.yaml\n")
        )
    assert yaml.safe_load(parsed) == {
        "some_yaml": [{"zoo": "bar", "moo": "jersey cow"}]
    }
