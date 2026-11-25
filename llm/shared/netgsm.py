"""Shared Netgsm call-center API helper.

Centralizes the Netgsm "netsantral/report" request that the audio-to-text
pipeline used to list call recordings. Credentials come from env.
"""
from __future__ import annotations

import requests

from . import config

REPORT_URL = "https://api.netgsm.com.tr/netsantral/report"


def fetch_call_report(start_date: str, stop_date: str, **extra) -> requests.Response:
    """POST a date-range report request to Netgsm and return the raw response."""
    payload = {
        "usercode": config.NETGSM_USERCODE,
        "password": config.NETGSM_PASSWORD,
        "startdate": start_date,
        "stopdate": stop_date,
        **extra,
    }
    return requests.post(REPORT_URL, data=payload, timeout=30)
