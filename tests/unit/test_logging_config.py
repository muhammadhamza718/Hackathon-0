"""Unit tests for agents.logging_config module."""

from __future__ import annotations

import logging

from agents.logging_config import configure_logging, get_logger


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
