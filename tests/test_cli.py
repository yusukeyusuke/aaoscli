import argparse
import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from aaos_cli import cli


class CliTest(unittest.TestCase):
    def test_print_refs_applies_filter_and_limit(self):
        output = io.StringIO()

        with redirect_stdout(output):
            cli.print_refs(
                ["android-15.0.0_r1", "android-14.0.0_r1", "platform-tools-35.0.0"],
                filter_text="android",
                limit=1,
            )

        self.assertEqual(output.getvalue(), "android-15.0.0_r1\n")

    def test_list_remote_refs_parses_git_ls_remote_output(self):
        completed = argparse.Namespace(
            stdout=(
                "abc123\trefs/tags/android-15.0.0_r1\n"
                "def456\trefs/tags/android-14.0.0_r1\n"
                "bad-line\n"
            ),
            stderr="",
        )

        with mock.patch.object(cli, "find_executable", return_value="/usr/bin/git"):
            with mock.patch.object(cli.subprocess, "run", return_value=completed) as run:
                refs = cli.list_remote_refs(
                    "https://android.googlesource.com/platform/manifest",
                    "refs/tags/",
                )

        self.assertEqual(refs, ["android-15.0.0_r1", "android-14.0.0_r1"])
        run.assert_called_once()

    def test_path_contains_matches_resolved_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            bin_dir = Path(tmp) / "bin"
            bin_dir.mkdir()

            with mock.patch.dict(os.environ, {"PATH": str(bin_dir)}):
                self.assertTrue(cli.path_contains(bin_dir))


if __name__ == "__main__":
    unittest.main()
