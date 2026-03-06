"""Unit tests for agents.logging_config module."""

from __future__ import annotations

import logging

import pytest

from agents.logging_config import Level, configure_logging, get_logger


def test_get_logger_returns_logger():
    logger = get_logger("test.module")
    assert isinstance(logger, logging.Logger)
    assert logger.name == "test.module"


def test_get_logger_unique_per_name():
    a = get_logger("a")
    b = get_logger("b")
    assert a is not b


def test_configure_logging_sets_level():
    configure_logging(level="DEBUG")
    assert logging.root.level == logging.DEBUG


def test_configure_logging_info_level():
    configure_logging(level="INFO")
    assert logging.root.level == logging.INFO


def test_configure_logging_warning_level():
    configure_logging(level="WARNING")
    assert logging.root.level == logging.WARNING


class TestLevelEnum:
    """Verify Level IntEnum maps to stdlib logging values."""

    @pytest.mark.parametrize(
        "level,stdlib_value",
        [
            (Level.DEBUG, logging.DEBUG),
            (Level.INFO, logging.INFO),
            (Level.WARNING, logging.WARNING),
            (Level.ERROR, logging.ERROR),
            (Level.CRITICAL, logging.CRITICAL),
        ],
    )
    def test_values_match_stdlib(self, level: Level, stdlib_value: int):
        assert level.value == stdlib_value

    def test_ordering(self):
        assert Level.DEBUG < Level.INFO < Level.WARNING < Level.ERROR < Level.CRITICAL

    def test_int_comparison(self):
        assert Level.INFO == 20
        assert Level.ERROR > 30
