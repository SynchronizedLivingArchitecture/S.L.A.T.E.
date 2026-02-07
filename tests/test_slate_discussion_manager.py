# Modified: 2026-02-07T13:35:00Z | Author: COPILOT | Change: Add test coverage for slate_discussion_manager module
"""
Tests for slate/slate_discussion_manager.py — discussion log operations,
event tracking, Q&A tracking, utility functions.
"""

import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from slate.slate_discussion_manager import (
    load_discussion_log,
    save_discussion_log,
    log_event,
    track_qa,
    ensure_log_directory,
    DISCUSSION_LOG_FILE,
)


# ── Fixtures ────────────────────────────────────────────────────────────


@pytest.fixture
def tmp_log(tmp_path):
    """Redirect discussion log to a temp directory."""
    log_file = tmp_path / "discussion_log.json"
    with patch("slate.slate_discussion_manager.DISCUSSION_LOG_FILE", log_file):
        yield log_file


# ── load/save discussion log ────────────────────────────────────────────


class TestDiscussionLog:
    """Tests for discussion log persistence."""

    def test_load_missing_returns_default(self, tmp_log):
        log = load_discussion_log()
        assert "events" in log
        assert "discussions" in log
        assert log["events"] == []

    def test_save_and_load_roundtrip(self, tmp_log):
        data = {"events": [{"event": "test"}], "discussions": {}}
        save_discussion_log(data)
        loaded = load_discussion_log()
        assert len(loaded["events"]) == 1
        assert loaded["events"][0]["event"] == "test"


# ── log_event ───────────────────────────────────────────────────────────


class TestLogEvent:
    """Tests for the log_event function."""

    def test_log_event_adds_entry(self, tmp_log):
        log_event("created", "42", title="Test Discussion", category="Q&A")
        log = load_discussion_log()
        assert len(log["events"]) == 1
        assert log["events"][0]["discussion"] == "42"

    def test_log_event_tracks_discussion_metadata(self, tmp_log):
        log_event("created", "42", title="Test Discussion", category="Q&A")
        log = load_discussion_log()
        assert "42" in log["discussions"]
        assert log["discussions"]["42"]["title"] == "Test Discussion"

    def test_multiple_events_same_discussion(self, tmp_log):
        log_event("created", "42", title="Test")
        log_event("commented", "42")
        log = load_discussion_log()
        assert len(log["events"]) == 2
        assert len(log["discussions"]["42"]["events"]) == 2


# ── track_qa ────────────────────────────────────────────────────────────


class TestTrackQA:
    """Tests for Q&A tracking."""

    def test_track_qa_creates_entry(self, tmp_log):
        track_qa("100")
        log = load_discussion_log()
        assert "qa_tracking" in log
        assert "100" in log["qa_tracking"]
        assert log["qa_tracking"]["100"]["answered"] is False

    def test_track_qa_idempotent(self, tmp_log):
        track_qa("100")
        track_qa("100")
        log = load_discussion_log()
        assert "100" in log["qa_tracking"]
