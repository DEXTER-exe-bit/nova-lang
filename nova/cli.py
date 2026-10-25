"""Command-line interface for Nova."""

import argparse
from pathlib import Path
from typing import Sequence

from . import NovaRuntimeError, NovaSyntaxError, run
from .compiler import NovaCompilerError, build_file

VERSION = "0.1.0"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="nova",
        description="Run programs written in the Nova language.",
    )
    parser.add_argument("--version", action="version", version=f"Nova {VERSION}")
    commands = parser.add_subparsers(dest="command", metavar="COMMAND")
    run_parser = commands.add_parser("run", help="execute a Nova source file")
    run_parser.add_argument("file", type=Path, metavar="FILE.nova", help="Nova source file to execute")
    build_parser = commands.add_parser("build", help="compile supported Nova into a native executable")
    build_parser.add_argument("file", type=Path, metavar="FILE.nova", help="Nova source file to compile")
    build_parser.add_argument("-o", "--output", type=Path, help="output executable path")
    build_parser.add_argument("--emit-c", type=Path, metavar="FILE.c", help="save generated C source")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the Nova command line interface and return a process exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.error("a command is required; use 'nova run FILE.nova'")

    if args.command == "run":
        try:
            source = args.file.read_text(encoding="utf-8")
        except FileNotFoundError:
            parser.error(f"file not found: {args.file}")
        except OSError as error:
            parser.error(f"could not read '{args.file}': {error}")
        try:
            run(source)
        except (NovaSyntaxError, NovaRuntimeError) as error:
            parser.exit(1, f"Nova error: {error}\n")
    else:
        try:
            output = build_file(args.file, args.output, args.emit_c)
        except (NovaSyntaxError, NovaCompilerError) as error:
            parser.exit(1, f"Nova build error: {error}\n")
        print(f"Built {output}")
    return 0
