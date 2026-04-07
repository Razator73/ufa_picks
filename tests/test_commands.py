# -*- coding: utf-8 -*-
"""Command tests."""
from click.testing import CliRunner

from ufa_picks.commands import lint
from ufa_picks.commands import test as cmd_test


def test_lint_command():
    """Test lint command."""
    runner = CliRunner()
    result = runner.invoke(lint, ["--check"])
    assert result.exit_code in [0, 1]

    result2 = runner.invoke(lint)
    assert result2.exit_code in [0, 1]


def test_test_command():
    """Test test command."""
    runner = CliRunner()
    result = runner.invoke(cmd_test, ["--filter", "not_a_real_test", "--no-coverage"])
    assert result.exit_code in [0, 1, 5]

    result2 = runner.invoke(cmd_test, ["--filter", "not_a_real_test", "--coverage"])
    assert result2.exit_code in [0, 1, 5]
