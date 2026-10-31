from __future__ import annotations

import subprocess

import pytest

from tourism_pipeline import tracking


def test_commit_declared_in_the_environment_is_used(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GIT_COMMIT", "0123456789abcdef0123456789abcdef01234567")

    assert tracking.git_commit() == "0123456789abcdef0123456789abcdef01234567"


def test_commit_comes_from_git_when_the_variable_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("GIT_COMMIT", raising=False)

    commit = tracking.git_commit()

    assert commit == "unknown" or len(commit) == 40


@pytest.mark.parametrize("declared", ["", "unknown", "  "])
def test_placeholder_values_fall_back_to_git(
    monkeypatch: pytest.MonkeyPatch, declared: str
) -> None:
    monkeypatch.setenv("GIT_COMMIT", declared)
    monkeypatch.setattr(
        tracking.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args, 0, stdout="abc123\n"),
    )

    assert tracking.git_commit() == "abc123"


def test_missing_git_binary_gives_unknown(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GIT_COMMIT", raising=False)

    def not_installed(*args, **kwargs):
        raise FileNotFoundError("git")

    monkeypatch.setattr(tracking.subprocess, "run", not_installed)

    assert tracking.git_commit() == "unknown"
