from __future__ import annotations

import argparse
import os
import stat
import subprocess
import sys
import urllib.request
from pathlib import Path
from typing import Iterable

from . import __version__


DEFAULT_MANIFEST_URL = "https://android.googlesource.com/platform/manifest"
DEFAULT_REPO_URL = "https://storage.googleapis.com/git-repo-downloads/repo"


class AaosError(RuntimeError):
    pass


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        return args.func(args)
    except AaosError as exc:
        print(f"aaos: error: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("aaos: interrupted", file=sys.stderr)
        return 130


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aaos",
        description="AAOS workspace helper CLI.",
    )
    parser.add_argument("--version", action="version", version=f"aaos {__version__}")

    subcommands = parser.add_subparsers(dest="command", required=True)

    repo = subcommands.add_parser("repo", help="Manage repo and AOSP manifest refs.")
    repo_subcommands = repo.add_subparsers(dest="repo_command", required=True)

    install = repo_subcommands.add_parser("install", help="Install the repo command.")
    install.add_argument(
        "--bin-dir",
        default=str(Path.home() / ".local" / "bin"),
        help="Directory to install repo into. Default: ~/.local/bin",
    )
    install.add_argument(
        "--url",
        default=DEFAULT_REPO_URL,
        help=f"repo script URL. Default: {DEFAULT_REPO_URL}",
    )
    install.add_argument(
        "--force",
        action="store_true",
        help="Overwrite an existing repo executable.",
    )
    install.set_defaults(func=cmd_repo_install)

    tags = repo_subcommands.add_parser("tags", help="List platform manifest tags.")
    add_ref_list_options(tags)
    tags.set_defaults(func=cmd_repo_tags)

    branches = repo_subcommands.add_parser(
        "branches",
        help="List platform manifest branches.",
    )
    add_ref_list_options(branches)
    branches.set_defaults(func=cmd_repo_branches)

    return parser


def add_ref_list_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--manifest-url",
        default=DEFAULT_MANIFEST_URL,
        help=f"Manifest repository URL. Default: {DEFAULT_MANIFEST_URL}",
    )
    parser.add_argument(
        "--filter",
        default=None,
        help="Only show refs containing this text.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of refs to show.",
    )


def cmd_repo_install(args: argparse.Namespace) -> int:
    bin_dir = Path(args.bin_dir).expanduser()
    target = bin_dir / "repo"

    if target.exists() and not args.force:
        raise AaosError(f"{target} already exists. Use --force to overwrite it.")

    bin_dir.mkdir(parents=True, exist_ok=True)

    try:
        with urllib.request.urlopen(args.url, timeout=60) as response:
            content = response.read()
    except OSError as exc:
        raise AaosError(f"failed to download repo from {args.url}: {exc}") from exc

    target.write_bytes(content)
    mode = target.stat().st_mode
    target.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    print(f"installed repo: {target}")
    if not path_contains(bin_dir):
        print(f"note: add {bin_dir} to PATH to run repo directly")
    return 0


def cmd_repo_tags(args: argparse.Namespace) -> int:
    refs = list_remote_refs(args.manifest_url, "refs/tags/")
    print_refs(refs, filter_text=args.filter, limit=args.limit)
    return 0


def cmd_repo_branches(args: argparse.Namespace) -> int:
    refs = list_remote_refs(args.manifest_url, "refs/heads/")
    print_refs(refs, filter_text=args.filter, limit=args.limit)
    return 0


def list_remote_refs(manifest_url: str, prefix: str) -> list[str]:
    git = find_executable("git")
    if git is None:
        raise AaosError("git is required but was not found in PATH")

    try:
        completed = subprocess.run(
            [git, "ls-remote", "--refs", manifest_url, f"{prefix}*"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        detail = exc.stderr.strip() or exc.stdout.strip()
        raise AaosError(f"failed to list refs from {manifest_url}: {detail}") from exc

    refs: list[str] = []
    for line in completed.stdout.splitlines():
        parts = line.split()
        if len(parts) != 2:
            continue
        ref = parts[1]
        if ref.startswith(prefix):
            refs.append(ref.removeprefix(prefix))

    refs.sort(reverse=True)
    return refs


def print_refs(
    refs: Iterable[str],
    *,
    filter_text: str | None,
    limit: int | None,
) -> None:
    shown = 0
    for ref in refs:
        if filter_text and filter_text not in ref:
            continue
        print(ref)
        shown += 1
        if limit is not None and shown >= limit:
            break


def find_executable(name: str) -> str | None:
    paths = os.environ.get("PATH", "").split(os.pathsep)
    for path in paths:
        candidate = Path(path) / name
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None


def path_contains(directory: Path) -> bool:
    target = directory.resolve()
    for item in os.environ.get("PATH", "").split(os.pathsep):
        if not item:
            continue
        try:
            if Path(item).expanduser().resolve() == target:
                return True
        except OSError:
            continue
    return False

