"""Backward-compatible module runner; use the installed ``nova`` command."""
import sys

from nova.cli import main


if __name__ == "__main__":
    raise SystemExit(main(["run", *sys.argv[1:]]))
