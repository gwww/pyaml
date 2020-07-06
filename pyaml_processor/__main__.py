import argparse
import logging
import os
import sys
import time

from pyaml_processor import pyaml_file

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def process_yaml(args):
    try:
        (lines, error) = pyaml_file(args.file[0], args.check)
        return (lines, error)
    except Exception as error:
        logger.exception(error)
        return ("", error)


def write_output(args, lines):
    if args.output:
        with open(args.output, "w") as stream:
            line_count = lines.count("\n")
            print(f"Writing {line_count} lines to '{args.output}'")
            stream.write(lines)
    else:
        sys.stdout.write(lines)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Process python embedded in YAML."
    )
    parser.add_argument(
        "-c",
        "--check",
        action="store_true",
        help="Check if YAML is valid and reformat it.",
        default=False,
    )
    parser.add_argument("-o", "--output", action="store", help="Output file.")
    parser.add_argument("file", nargs=1, help="YAML file with embedded Python.")
    return parser.parse_args()


def main():
    args = parse_args()

    (lines, error) = process_yaml(args)
    if not error:
        write_output(args, lines)
    exit(-1 if error else 0)


if __name__ == "__main__":
    sys.exit(main())
