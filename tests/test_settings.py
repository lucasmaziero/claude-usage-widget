"""Preference load, clamp and save."""
from __future__ import annotations

import json
from pathlib import Path

from agent_gauge.settings import DEFAULTS, MAX_POLL, MIN_POLL, Settings


def test_defaults_when_no_file(tmp_path: Path):
    s = Settings(tmp_path / "settings.json")
    assert dict(s) == DEFAULTS


def test_stored_values_win_and_unknown_keys_are_dropped(tmp_path: Path):
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"poll_sec": 300, "leftover": 1}), encoding="utf-8")

    s = Settings(path)
    assert s["poll_sec"] == 300
    assert "leftover" not in s


def test_poll_interval_is_clamped(tmp_path: Path):
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"poll_sec": 5}), encoding="utf-8")
    assert Settings(path)["poll_sec"] == MIN_POLL

    path.write_text(json.dumps({"poll_sec": 99_999}), encoding="utf-8")
    assert Settings(path)["poll_sec"] == MAX_POLL


def test_save_round_trip(tmp_path: Path):
    path = tmp_path / "sub" / "settings.json"
    s = Settings(path)
    s["pos_x"], s["pos_y"] = 100, 200
    s.save()

    assert Settings(path)["pos_x"] == 100
    assert Settings(path)["pos_y"] == 200


def test_corrupt_file_falls_back_to_defaults(tmp_path: Path):
    path = tmp_path / "settings.json"
    path.write_text("{not json", encoding="utf-8")
    assert Settings(path)["poll_sec"] == DEFAULTS["poll_sec"]
