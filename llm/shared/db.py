"""Shared MySQL helper.

Consolidates the duplicated `create_connection()` + settings/`ayarlar`-table
lookups that appeared in both the audio-to-text pipeline and the tour agent.
Credentials come from `shared.config` (environment), never hardcoded.
"""
from __future__ import annotations

import logging

import mysql.connector
from mysql.connector import Error

from . import config

log = logging.getLogger(__name__)


def create_connection():
    """Open a MySQL connection using env-based config. Returns None on failure."""
    try:
        return mysql.connector.connect(**config.db_config())
    except Error as exc:  # noqa: BLE001
        log.error("DB connection failed: %s", exc)
        return None


def get_setting(cursor, key: str) -> str | None:
    """Read a single value from the key/value `ayarlar` settings table."""
    cursor.execute("SELECT deger FROM ayarlar WHERE anahtar = %s", (key,))
    row = cursor.fetchone()
    return row[0] if row and row[0] else None


def get_api_key(cursor, *keys: str) -> str | None:
    """Return the first non-empty API key stored under any of `keys`."""
    for key in keys:
        val = get_setting(cursor, key)
        if val:
            return val
    return None
