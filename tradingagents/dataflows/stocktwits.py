"""StockTwits public symbol-stream fetcher.

StockTwits exposes a per-symbol message stream at
``api.stocktwits.com/api/2/streams/symbol/{ticker}.json`` that requires no
API key, no OAuth, and no registration. Each message includes a
user-labeled sentiment field (``Bullish``/``Bearish``/null), the message
body, timestamp, and posting user.

The function is deliberately self-contained: short timeout, graceful
degradation on any HTTP or parse failure, and a string return type so
the calling agent gets a uniform interface regardless of whether the
network call succeeded.
"""

from __future__ import annotations

import http.client
import json
import logging
from urllib.request import Request, urlopen

from .symbol_utils import get_stocktwits_symbol

logger = logging.getLogger(__name__)

import os

_API = "https://stocktwits.p.rapidapi.com/streams/symbol/{ticker}.json"
_RAPIDAPI_KEY = os.environ.get("RAPIDAPI_KEY", "")
_RAPIDAPI_HOST = "stocktwits.p.rapidapi.com"
_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) MyTradingAgent/1.0"


def _stocktwits_symbol(ticker: str) -> str:
    """Map a symbol to StockTwits' convention."""
    return get_stocktwits_symbol(ticker)


def fetch_stocktwits_messages(ticker: str, limit: int = 30, timeout: float = 10.0) -> str:
    """Fetch recent StockTwits messages for ``ticker`` and return them as a
    formatted plaintext block ready for prompt injection.

    Returns a placeholder string when the endpoint is unreachable, the
    symbol has no messages, or the response shape is unexpected — the
    caller never has to special-case None or exceptions.
    """
    url = _API.format(ticker=_stocktwits_symbol(ticker))
    headers = {
        "User-Agent": _UA, 
        "Accept": "application/json",
        "X-RapidAPI-Key": _RAPIDAPI_KEY,
        "X-RapidAPI-Host": _RAPIDAPI_HOST
    }
    req = Request(url, headers=headers)
    try:
        with urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read())
    except (OSError, http.client.HTTPException, json.JSONDecodeError) as exc:
        # OSError covers URLError/TimeoutError/connection resets; HTTPException
        # covers chunked-transfer errors (IncompleteRead/BadStatusLine, #1024).
        logger.warning("StockTwits fetch failed for %s: %s", ticker, exc)
        return f"<stocktwits unavailable: {type(exc).__name__}>"

    messages = data.get("messages", []) if isinstance(data, dict) else []
    if not messages:
        return f"<no StockTwits messages found for ${ticker.upper()}>"

    lines = []
    bullish = bearish = unlabeled = 0
    for m in messages[:limit]:
        created = m.get("created_at", "")
        user = (m.get("user") or {}).get("username", "?")
        entities = m.get("entities") or {}
        sentiment_obj = entities.get("sentiment") or {}
        sentiment = sentiment_obj.get("basic") if isinstance(sentiment_obj, dict) else None
        body = (m.get("body") or "").replace("\n", " ").strip()
        if len(body) > 280:
            body = body[:280] + "…"

        if sentiment == "Bullish":
            bullish += 1
            tag = "Bullish"
        elif sentiment == "Bearish":
            bearish += 1
            tag = "Bearish"
        else:
            unlabeled += 1
            tag = "no-label"
        lines.append(f"[{created} · @{user} · {tag}] {body}")

    total = bullish + bearish + unlabeled
    bull_pct = round(100 * bullish / total) if total else 0
    bear_pct = round(100 * bearish / total) if total else 0
    summary = (
        f"Bullish: {bullish} ({bull_pct}%) · "
        f"Bearish: {bearish} ({bear_pct}%) · "
        f"Unlabeled: {unlabeled} · "
        f"Total: {total} most-recent messages"
    )
    return summary + "\n\n" + "\n".join(lines)
