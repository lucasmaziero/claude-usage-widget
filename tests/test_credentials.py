"""Token loading, including the macOS keychain path that cannot be exercised on
the machine this is developed on."""
from __future__ import annotations

import json
import subprocess

import pytest

from agent_gauge import credentials, i18n

BLOB = {
    "claudeAiOauth": {
        "accessToken": "sk-ant-oat-file",
        "expiresAt": 4_102_444_800_000,      # 2100, comfortably unexpired
        "subscriptionType": "max",
        "rateLimitTier": "default",
    }
}


@pytest.fixture
def creds_file(tmp_path):
    path = tmp_path / ".credentials.json"
    path.write_text(json.dumps(BLOB), encoding="utf-8")
    return path


@pytest.fixture(autouse=True)
def _english():
    """Error messages are asserted by their words, so pin the language rather
    than inherit whatever the developer's desktop is set to."""
    before = i18n.language()
    i18n.set_language("en")
    yield
    i18n.set_language(before)


@pytest.fixture(autouse=True)
def not_macos(monkeypatch):
    """Default every test to the file path; the keychain tests opt back in."""
    monkeypatch.setattr(credentials, "MACOS", False)


def test_reads_the_file(creds_file):
    creds = credentials.load(creds_file)
    assert creds.token == "sk-ant-oat-file"
    assert creds.subscription == "max"
    assert not creds.expired


def test_missing_file_names_the_path(tmp_path):
    missing = tmp_path / "nope.json"
    with pytest.raises(credentials.CredentialsError, match=r"nope.json"):
        credentials.load(missing)


def test_blob_without_a_token_is_rejected(tmp_path):
    path = tmp_path / ".credentials.json"
    path.write_text(json.dumps({"claudeAiOauth": {}}), encoding="utf-8")
    with pytest.raises(credentials.CredentialsError, match="accessToken"):
        credentials.load(path)


def test_malformed_json_is_reported_not_raised_raw(tmp_path):
    path = tmp_path / ".credentials.json"
    path.write_text("{ not json", encoding="utf-8")
    with pytest.raises(credentials.CredentialsError):
        credentials.load(path)


# ------------------------------------------------------------------- macOS
@pytest.fixture
def macos(monkeypatch):
    monkeypatch.setattr(credentials, "MACOS", True)


def _security(stdout: str, returncode: int = 0):
    def fake(argv, **kwargs):
        assert argv[0] == "security"
        assert credentials.KEYCHAIN_SERVICE in argv
        return subprocess.CompletedProcess(argv, returncode, stdout=stdout, stderr="")
    return fake


def test_keychain_wins_over_the_file(macos, creds_file, monkeypatch):
    """Both present: the keychain is where Claude Code actually writes on macOS."""
    keychain = json.dumps({"claudeAiOauth": {"accessToken": "sk-ant-oat-keychain"}})
    monkeypatch.setattr(subprocess, "run", _security(keychain + "\n"))
    assert credentials.load(creds_file).token == "sk-ant-oat-keychain"


def test_falls_back_to_the_file_when_the_keychain_is_empty(macos, creds_file, monkeypatch):
    monkeypatch.setattr(subprocess, "run", _security("", returncode=44))
    assert credentials.load(creds_file).token == "sk-ant-oat-file"


def test_neither_source_reports_the_keychain(macos, tmp_path, monkeypatch):
    monkeypatch.setattr(subprocess, "run", _security("", returncode=44))
    with pytest.raises(credentials.CredentialsError, match="keychain"):
        credentials.load(tmp_path / "absent.json")


def test_security_missing_is_not_a_crash(macos, creds_file, monkeypatch):
    """No `security` binary, or a denied prompt: fall through, never raise."""
    def boom(argv, **kwargs):
        raise OSError("no such file")
    monkeypatch.setattr(subprocess, "run", boom)
    assert credentials.load(creds_file).token == "sk-ant-oat-file"


def test_security_timeout_is_not_a_crash(macos, creds_file, monkeypatch):
    def slow(argv, **kwargs):
        raise subprocess.TimeoutExpired(argv, credentials.KEYCHAIN_TIMEOUT)
    monkeypatch.setattr(subprocess, "run", slow)
    assert credentials.load(creds_file).token == "sk-ant-oat-file"
