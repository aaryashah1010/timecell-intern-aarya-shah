"""Tests for the combined main.py task dispatcher."""

from __future__ import annotations

import sys

import main as combined_main
import task1_risk
import task4_crash_story


def test_main_without_task_shows_menu_and_exits(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["main.py"])
    monkeypatch.setattr("builtins.input", lambda prompt: "0")

    result = combined_main.main()

    out = capsys.readouterr().out
    assert result == 0
    assert "Choose a task to run" in out
    assert "1. Task 1 - Portfolio Risk Calculator" in out
    assert "4. Task 4 - Crash Scenario Story Generator" in out


def test_main_menu_choice_runs_task1(monkeypatch):
    seen = {}

    def fake_task1_main() -> int:
        seen["argv"] = sys.argv[:]
        return 3

    monkeypatch.setattr(task1_risk, "main", fake_task1_main)
    monkeypatch.setattr(sys, "argv", ["main.py"])
    monkeypatch.setattr("builtins.input", lambda prompt: "1")

    result = combined_main.main()

    assert result == 3
    assert seen["argv"] == ["task1_risk.py"]


def test_main_forwards_task_specific_args_to_task1(monkeypatch):
    seen = {}

    def fake_task1_main() -> int:
        seen["argv"] = sys.argv[:]
        return 7

    monkeypatch.setattr(task1_risk, "main", fake_task1_main)
    monkeypatch.setattr(sys, "argv", ["main.py", "--task1", "--compare"])

    result = combined_main.main()

    assert result == 7
    assert seen["argv"] == ["task1_risk.py", "--compare"]
    assert sys.argv == ["main.py", "--task1", "--compare"]


def test_main_crash_story_alias_forwards_args_to_task4(monkeypatch):
    seen = {}

    def fake_task4_main(args: list[str] | None = None) -> int:
        seen["args"] = args
        return 9

    monkeypatch.setattr(task4_crash_story, "main", fake_task4_main)
    monkeypatch.setattr(sys, "argv", ["main.py", "--crash-story", "--dry-run"])

    result = combined_main.main()

    assert result == 9
    assert seen["args"] == ["--dry-run"]
