#!/usr/bin/env python3
from forgetree.cli.utils import print_tree


if __name__ == "__main__":

    from argparse import ArgumentParser
    #from forgetree.cli.utils import print_tree

    parser = ArgumentParser(
        description="Print a project directory tree with helpful inline comments."
    )
    parser.add_argument(
        "root",
        nargs="?",
        default=".",
        help="Root directory to scan (default: current directory)",
    )
    parser.add_argument(
        "--depth",
        "-d",
        type=int,
        default=None,
        help="Maximum recursion depth (default: unlimited)",
    )
    parser.add_argument(
        "--ignore",
        "-i",
        nargs="*",
        default=[],
        help="Additional glob patterns to ignore (e.g. '*.log' 'tmp')",
    )
    parser.add_argument(
        "--no-gitignore",
        action="store_true",
        help="Skip .gitignore parsing",
    )
    args = parser.parse_args()

    print_tree(
        args.root,
        ignore=set(args.ignore),
        max_depth=args.depth,
        use_gitignore=not args.no_gitignore,
    )

