from cli.parser import parse_args
from cli.executor import execute


def run(argv: list[str]) -> str:
    args = parse_args(argv)
    # BUG: dry_run parsed but not passed to executor.
    return execute(args["target"])
