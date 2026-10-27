"""Test module for file ui/__init__.py"""

import io
import sys
import unittest
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path
from random import random
from unittest.mock import patch

import pytest

from beets import config, ui
from beets.exceptions import UserError
from beets.test.helper import BeetsTestCase, IOMixin


class InputMethodsTest(IOMixin, unittest.TestCase):
    def _print_helper(self, s):
        print(s)

    def _print_helper2(self, s, prefix):
        print(prefix, s)

    def test_input_select_objects(self):
        full_items = ["1", "2", "3", "4", "5"]

        # Test no
        self.io.addinput("n")
        items = ui.input_select_objects(
            "Prompt", full_items, self._print_helper
        )
        assert items == []

        # Test yes
        self.io.addinput("y")
        items = ui.input_select_objects(
            "Prompt", full_items, self._print_helper
        )
        assert items == full_items

        # Test selective 1
        self.io.addinput("s")
        self.io.addinput("n")
        self.io.addinput("y")
        self.io.addinput("n")
        self.io.addinput("y")
        self.io.addinput("n")
        items = ui.input_select_objects(
            "Prompt", full_items, self._print_helper
        )
        assert items == ["2", "4"]

        # Test selective 2
        self.io.addinput("s")
        self.io.addinput("y")
        self.io.addinput("y")
        self.io.addinput("n")
        self.io.addinput("y")
        self.io.addinput("n")
        items = ui.input_select_objects(
            "Prompt", full_items, lambda s: self._print_helper2(s, "Prefix")
        )
        assert items == ["1", "2", "4"]

        # Test selective 3
        self.io.addinput("s")
        self.io.addinput("y")
        self.io.addinput("n")
        self.io.addinput("y")
        self.io.addinput("q")
        items = ui.input_select_objects(
            "Prompt", full_items, self._print_helper
        )
        assert items == ["1", "3"]


class ParentalDirCreation(IOMixin, BeetsTestCase):
    def test_memory_path_skips_creation_prompt(self):
        ui._ensure_db_directory_exists(Path(":memory:"))
        assert not self.io.getoutput()

    def test_create_yes(self):
        non_exist_path = self.temp_path / "nonexist" / str(random())
        # Deepcopy instead of recovering because exceptions might
        # occur; wish I can use a golang defer here.
        test_config = deepcopy(config)
        test_config["library"] = str(non_exist_path)
        self.io.addinput("y")
        lib = ui._open_library(test_config)
        lib._close()

    def test_create_no(self):
        non_exist_path_parent = self.temp_path / "nonexist"
        non_exist_path = non_exist_path_parent / str(random())
        test_config = deepcopy(config)
        test_config["library"] = str(non_exist_path)

        self.io.addinput("n")
        with pytest.raises(UserError):
            ui._open_library(test_config)
        assert not non_exist_path_parent.exists()


@contextmanager
def fake_stderr(tty=True):
    """Replace stderr with a buffer that does or does not look like a TTY."""
    err = io.StringIO()
    err.isatty = lambda: tty
    with (
        patch.object(sys, "stderr", err),
        patch.object(sys, "platform", "linux"),
        patch.object(ui, "term_width", lambda: 80),
    ):
        yield err


class TestProgress:
    def test_yields_all_items_unchanged(self):
        with fake_stderr():
            assert list(ui.progress([1, 2, 3], "Working")) == [1, 2, 3]

    def test_draws_counts_and_erases_when_done(self):
        with fake_stderr() as err:
            list(ui.progress(["a", "b"], "Working"))
        out = err.getvalue()
        assert "Working |--------------------| 0/2 items" in out
        assert "Working |##########----------| 1/2 items" in out
        assert "Working |####################| 2/2 items" in out
        assert out.endswith("\r\x1b[2K")

    def test_bar_is_erased_while_loop_body_runs(self):
        with fake_stderr() as err:
            for _ in ui.progress(["a"], "Working"):
                assert err.getvalue().endswith("\r\x1b[2K")

    def test_unknown_total_shows_running_count(self):
        with fake_stderr() as err:
            list(ui.progress((i for i in range(2)), "Working"))
        assert "Working 2 items" in err.getvalue()

    def test_erased_when_loop_is_abandoned(self):
        with fake_stderr() as err:
            for _ in ui.progress([1, 2, 3], "Working"):
                break
        assert err.getvalue().endswith("\r\x1b[2K")

    def test_silent_when_not_a_tty(self):
        with fake_stderr(tty=False) as err:
            assert list(ui.progress([1, 2], "Working")) == [1, 2]
        assert err.getvalue() == ""
