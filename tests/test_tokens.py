"""Token counting over Claude Code transcripts."""
from __future__ import annotations

import json
import time
from datetime import UTC, datetime
from pathlib import Path

from claude_usage import tokens


def _line(msg_id: str, when: float, **usage: int) -> str:
    return json.dumps({
        "timestamp": datetime.fromtimestamp(when, UTC).isoformat().replace("+00:00", "Z"),
        "uuid": f"uuid-{msg_id}",
        "message": {"id": msg_id, "usage": usage},
    })


def _transcript(root: Path, project: str, name: str, lines: list[str]) -> Path:
    path = root / project / f"{name}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def test_sums_input_output_and_cache(tmp_path: Path):
    now = time.time()
    _transcript(tmp_path, "proj", "a", [
        _line("m1", now, input_tokens=100, output_tokens=20, cache_read_input_tokens=1_000),
        _line("m2", now, input_tokens=50, cache_creation_input_tokens=10, output_tokens=5),
    ])

    totals = tokens.collect(now - 60, projects=tmp_path)
    assert totals.input == 160          # 100 + 50 + 10 of cache creation
    assert totals.output == 25
    assert totals.cache_read == 1_000
    assert totals.total == 185
    assert totals.sessions == 1


def test_messages_before_the_window_are_ignored(tmp_path: Path):
    now = time.time()
    _transcript(tmp_path, "proj", "a", [
        _line("old", now - 7200, input_tokens=999, output_tokens=999),
        _line("new", now, input_tokens=1, output_tokens=2),
    ])

    totals = tokens.collect(now - 60, projects=tmp_path)
    assert totals.input == 1
    assert totals.output == 2


def test_repeated_message_ids_count_once(tmp_path: Path):
    # Resuming a session re-writes earlier messages into the transcript.
    now = time.time()
    _transcript(tmp_path, "proj", "a", [
        _line("m1", now, input_tokens=10, output_tokens=1),
        _line("m1", now, input_tokens=10, output_tokens=1),
    ])

    totals = tokens.collect(now - 60, projects=tmp_path)
    assert totals.input == 10
    assert totals.output == 1


def test_sessions_count_distinct_files(tmp_path: Path):
    now = time.time()
    _transcript(tmp_path, "proj-a", "s1", [_line("m1", now, input_tokens=1)])
    _transcript(tmp_path, "proj-b", "s2", [_line("m2", now, input_tokens=1)])

    assert tokens.collect(now - 60, projects=tmp_path).sessions == 2


def test_malformed_lines_are_skipped(tmp_path: Path):
    now = time.time()
    _transcript(tmp_path, "proj", "a", [
        '{"usage": broken json',
        _line("m1", now, input_tokens=7),
    ])

    assert tokens.collect(now - 60, projects=tmp_path).input == 7


def test_missing_projects_directory_is_not_an_error(tmp_path: Path):
    totals = tokens.collect(time.time() - 60, projects=tmp_path / "nope")
    assert totals.total == 0
    assert totals.sessions == 0


def test_window_start_uses_the_reset_header():
    now = 1_800_000_000
    assert tokens.window_start(now + 3600, now=now) == now + 3600 - tokens.WINDOW_SECONDS


def test_window_start_falls_back_when_reset_is_stale():
    now = 1_800_000_000
    assert tokens.window_start(0, now=now) == now - tokens.WINDOW_SECONDS
