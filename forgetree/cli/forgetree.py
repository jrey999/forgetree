"""
project_structure.py
────────────────────
Generate a pretty ASCII project-structure tree by walking a real directory.

If a .gitignore is found at the project root, its patterns are automatically
parsed and merged into the ignore list — so the tree matches what Git sees.

Usage
-----
    from project_structure import print_tree, get_tree

    # Print to stdout (auto-reads .gitignore if present)
    print_tree("/path/to/my_project")

    # Get as a string (e.g. to write into a README)
    tree_str = get_tree("/path/to/my_project")
    print(tree_str)

    # Ignore extra patterns on top of the defaults + .gitignore
    print_tree(".", ignore={"dist", "*.egg-info"})

    # Skip .gitignore parsing
    print_tree(".", use_gitignore=False)
"""

from __future__ import annotations

import fnmatch
from pathlib import Path
from forgetree.cli.constants import FILE_COMMENTS, DIR_COMMENTS, DEFAULT_IGNORE


# ── .gitignore parser ─────────────────────────────────────────────────────────

def parse_gitignore(root: Path) -> set[str]:
    """
    Read ``<root>/.gitignore`` and return a set of glob patterns suitable for
    use with :func:`fnmatch.fnmatch`.

    Rules applied
    -------------
    * Blank lines and lines starting with ``#`` are skipped.
    * A leading ``/`` anchors the pattern to the root — the slash is stripped
      because we match against bare file/dir names, not full paths.
    * A trailing ``/`` means "directories only" in Git, but since we match by
      name we keep the pattern without the slash so it still filters the dir.
    * Negation patterns (``!``) are noted but not applied — they are uncommon
      and skipping them is the safe/conservative choice (the entry stays hidden).
    * ``**`` double-star patterns are simplified to ``*`` so fnmatch can handle
      them (fnmatch doesn't support ``**``).
    """
    gitignore = root / ".gitignore"
    if not gitignore.is_file():
        return set()

    patterns: set[str] = set()
    for raw_line in gitignore.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw_line.strip()

        # Skip blank lines and comments
        if not line or line.startswith("#"):
            continue

        # Skip negation patterns (safe to leave those files visible)
        if line.startswith("!"):
            continue

        # Strip leading slash (root-anchor) — we match on name only
        if line.startswith("/"):
            line = line[1:]

        # Strip trailing slash (directory marker) — we match by name anyway
        if line.endswith("/"):
            line = line[:-1]

        # Simplify **  →  * so fnmatch understands it
        line = line.replace("**", "*")

        if line:
            patterns.add(line)

    return patterns


# ── Core rendering logic ───────────────────────────────────────────────────────

def _should_ignore(name: str, patterns: set[str]) -> bool:
    """Return True if *name* matches any ignore glob pattern."""
    return any(fnmatch.fnmatch(name, pat) for pat in patterns)


def _get_comment(name: str, is_dir: bool) -> str:
    if is_dir:
        return DIR_COMMENTS.get(name.lower(), "")
    return FILE_COMMENTS.get(name) or FILE_COMMENTS.get(name.lower(), "")


def _render(
    path: Path,
    prefix: str,
    ignore: set[str],
    max_depth: int | None,
    current_depth: int,
) -> list[str]:
    """
    Recursively collect tree lines for the children of *path*.
    *prefix* is the leading whitespace / connector string for this level.
    """
    lines: list[str] = []

    # Gather and filter children
    try:
        children = [c for c in path.iterdir() if not _should_ignore(c.name, ignore)]
    except PermissionError:
        return ["  [permission denied]"]

    # Sort: directories first, then files — both groups case-insensitively
    children.sort(key=lambda p: (not p.is_dir(), p.name.lower()))

    for idx, child in enumerate(children):
        is_last = idx == len(children) - 1
        connector = "└── " if is_last else "├── "
        extension = "    " if is_last else "│   "

        is_dir = child.is_dir()
        display_name = child.name + "/" if is_dir else child.name
        comment = _get_comment(child.name, is_dir)
        comment_str = f"   # {comment}" if comment else ""

        lines.append(f"{prefix}{connector}{display_name}{comment_str}")

        # Recurse into directories (unless depth limit reached)
        if is_dir:
            at_limit = max_depth is not None and current_depth >= max_depth
            if at_limit:
                lines.append(f"{prefix}{extension}└── …")
            else:
                lines.extend(
                    _render(child, prefix + extension, ignore, max_depth, current_depth + 1)
                )

    return lines


# ── Public API ─────────────────────────────────────────────────────────────────

def get_tree(
    root: str | Path = ".",
    *,
    ignore: set[str] | None = None,
    max_depth: int | None = None,
    use_gitignore: bool = True,
) -> str:
    """
    Walk *root* and return the project-structure tree as a string.

    Parameters
    ----------
    root:
        Path to the project root directory.
    ignore:
        Extra glob patterns to skip, merged with DEFAULT_IGNORE (and
        .gitignore patterns if *use_gitignore* is True).
    max_depth:
        Maximum directory depth to recurse (None = unlimited).
    use_gitignore:
        If True (default), parse ``<root>/.gitignore`` and add its
        patterns to the ignore list automatically.

    Returns
    -------
    str
        Multi-line ASCII tree, ready to paste into a README.
    """
    root = Path(root).resolve()
    if not root.is_dir():
        raise NotADirectoryError(f"{root} is not a directory")

    patterns = DEFAULT_IGNORE | (ignore or set())

    if use_gitignore:
        gitignore_patterns = parse_gitignore(root)
        patterns |= gitignore_patterns

    comment = _get_comment(root.name, is_dir=True)
    comment_str = f"   # {comment}" if comment else ""
    header = f"{root.name}/{comment_str}"

    body = _render(root, "", patterns, max_depth, current_depth=1)
    return "\n".join([header] + body)


def print_tree(
    root: str | Path = ".",
    *,
    ignore: set[str] | None = None,
    max_depth: int | None = None,
    use_gitignore: bool = True,
) -> None:
    """Print the project-structure tree to stdout."""
    print(get_tree(root, ignore=ignore, max_depth=max_depth, use_gitignore=use_gitignore))