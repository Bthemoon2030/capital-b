"""Historische crypto-bars ophalen bij Alpaca.

Alleen stdlib (urllib), zodat er niets geinstalleerd hoeft te worden.

LET OP: deze code is hier geschreven zonder netwerktoegang, dus de endpoints
zijn niet live getest. Controleer ze tegen de actuele Alpaca-docs voordat je
op de uitkomst vertrouwt; Alpaca heeft de crypto-API al eens geversied
(v1beta1 -> v1beta3).
"""

from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from engine.types import Bar

DATA_BASE = "https://data.alpaca.markets/v1beta3/crypto/us"

TIMEFRAMES = {"1h": "1Hour", "4h": "4Hour", "1d": "1Day", "1w": "1Week"}


def _headers() -> dict[str, str]:
    key = os.environ.get("ALPACA_API_KEY_ID")
    secret = os.environ.get("ALPACA_API_SECRET_KEY")
    if not key or not secret:
        # Crypto-marktdata is bij Alpaca deels publiek; auth mag ontbreken.
        return {}
    return {"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": secret}


def _get(url: str) -> dict:
    request = urllib.request.Request(url, headers=_headers())
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode())


def fetch_bars(
    symbol: str = "BTC/USD",
    timeframe: str = "1d",
    start: str = "2020-01-01",
    end: str | None = None,
) -> list[Bar]:
    """Haal bars op, met paginatie tot alles binnen is."""
    if timeframe not in TIMEFRAMES:
        raise ValueError(f"timeframe moet een van {list(TIMEFRAMES)} zijn")

    bars: list[Bar] = []
    page_token: str | None = None

    while True:
        params = {
            "symbols": symbol,
            "timeframe": TIMEFRAMES[timeframe],
            "start": start,
            "limit": "10000",
        }
        if end:
            params["end"] = end
        if page_token:
            params["page_token"] = page_token

        payload = _get(f"{DATA_BASE}/bars?{urllib.parse.urlencode(params)}")

        for raw in payload.get("bars", {}).get(symbol, []):
            bars.append(
                Bar(
                    ts=datetime.fromisoformat(raw["t"].replace("Z", "+00:00")).astimezone(timezone.utc),
                    open=float(raw["o"]),
                    high=float(raw["h"]),
                    low=float(raw["l"]),
                    close=float(raw["c"]),
                    volume=float(raw.get("v", 0.0)),
                )
            )

        page_token = payload.get("next_page_token")
        if not page_token:
            break

    bars.sort(key=lambda b: b.ts)
    return bars


def save_csv(bars: list[Bar], path: str) -> None:
    """Wegschrijven zodat je daarna offline kunt backtesten."""
    import csv

    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["time", "open", "high", "low", "close", "volume"])
        for bar in bars:
            writer.writerow(
                [bar.ts.isoformat(), bar.open, bar.high, bar.low, bar.close, bar.volume]
            )


if __name__ == "__main__":
    import sys

    tf = sys.argv[1] if len(sys.argv) > 1 else "1d"
    out = sys.argv[2] if len(sys.argv) > 2 else f"data/btc_{tf}.csv"
    fetched = fetch_bars(timeframe=tf)
    save_csv(fetched, out)
    print(f"{len(fetched)} bars opgeslagen in {out}")
