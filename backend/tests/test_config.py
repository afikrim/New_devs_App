"""Tests for required-configuration validation.

These cover ``Settings.missing_database_settings()``, which the app calls at
startup to fail fast when the database is misconfigured (instead of silently
falling back to mock data).
"""

import pytest

from app.config import REQUIRED_DATABASE_SETTINGS, Settings


def test_defaults_are_complete():
    """With the shipped defaults, nothing is reported as missing."""
    assert Settings().missing_database_settings() == []


@pytest.mark.parametrize("field", ["supabase_db_user", "supabase_db_host", "supabase_db_name"])
def test_blank_string_field_is_missing(field):
    """A required string set to empty/whitespace is flagged as missing."""
    settings = Settings(**{field: "   "})
    assert settings.missing_database_settings() == [field]


def test_non_positive_port_is_missing():
    """A port of 0 (or negative) is not a usable value."""
    settings = Settings(supabase_db_port=0)
    assert "supabase_db_port" in settings.missing_database_settings()


def test_reports_every_missing_field():
    """All blank required fields are reported, not just the first."""
    blanks = {f: "" for f in REQUIRED_DATABASE_SETTINGS if f != "supabase_db_port"}
    blanks["supabase_db_port"] = 0
    missing = Settings(**blanks).missing_database_settings()
    assert set(missing) == set(REQUIRED_DATABASE_SETTINGS)
