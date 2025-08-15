from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict
import time
import random

import requests

ENDPOINT = "https://eportal.incometax.gov.in/iec/oursuccessenablers/saveData"


@dataclass(frozen=True)
class StatsPayload:
    indv_reg_users: int
    e_verified_returns: int
    total_aadhar_linked_pan: int
    total_processed_refund: int
    provider_last_updated_raw: str | None

    @staticmethod
    def from_json(data: Dict[str, Any]) -> "StatsPayload":
        return StatsPayload(
            indv_reg_users=int(data.get("IndvRegUsers") or 0),
            e_verified_returns=int(data.get("eVerifiedReturns") or 0),
            total_aadhar_linked_pan=int(data.get("TotalAadharLinkedPAN") or 0),
            total_processed_refund=int(data.get("TotalProcessedRefund") or 0),
            provider_last_updated_raw=(data.get("LastUpdated") if data.get("LastUpdated") else None),
        )


def _build_headers() -> Dict[str, str]:
    user_agents = [
        # Popular desktop browsers
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:127.0) Gecko/20100101 Firefox/127.0",
        # Mobile browsers
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1",
        "Mozilla/5.0 (Linux; Android 14; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Mobile Safari/537.36",
    ]
    accept_languages = [
        "en-IN,en;q=0.9",
        "en-US,en;q=0.9",
        "en-GB,en;q=0.9",
        "en-IN,hi-IN;q=0.8,en;q=0.7",
    ]
    headers = {
        "Accept": "application/json, text/plain, */*",
        "User-Agent": random.choice(user_agents),
        "Accept-Language": random.choice(accept_languages),
        "Connection": "keep-alive",
        # Using a generic portal page as referer to look like regular navigation
        "Referer": "https://eportal.incometax.gov.in/iec/foportal/en/",
    }
    return headers


def fetch_stats(timeout_seconds: int = 20, max_attempts: int = 5) -> StatsPayload:
    last_exc: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            # Small jitter to look less bot-like
            time.sleep(random.uniform(0.2, 0.9))
            response = requests.get(ENDPOINT, headers=_build_headers(), timeout=timeout_seconds)
            response.raise_for_status()
            data = response.json()
            return StatsPayload.from_json(data)
        except Exception as exc:  # network/HTTP/JSON
            last_exc = exc
            if attempt == max_attempts:
                break
            backoff = min(2 ** (attempt - 1), 30) + random.uniform(0.0, 0.5)
            time.sleep(backoff)
    assert last_exc is not None
    raise last_exc


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
