"""CSV inlezen, o.a. TradingView-exports.

TradingView schrijft kolomnamen die per export verschillen (`time` als unix
seconden of als ISO-string, `Volume` met hoofdletter, soms extra
indicatorkolommen). Deze loader is daar tolerant in in plaats van een vast
formaat af te dwingen.
"""

from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path

from engine.types import Bar

_ALIASES = {
    "ts": {"time", "timestamp", "date", "datetime", "open time"},
    "open": {"open", "o"},
    "high": {"high", "h"},
    "low": {"low", "l"},
    "close": {"close", "c", "close/last", "price"},
    "volume": {"volume", "v", "vol", "volume btc"},
}


def _resolve_columns(header: list[str]) -> dict[str, str]:
    lowered = {h.strip().lower(): h for h in header}
    mapping: dict[str, str] = {}
    for field, names in _ALIASES.items():
        for candidate in names:
            if candidate in lowered:
                mapping[field] = lowered[candidate]
                break
    missing = {"ts", "open", "high", "low", "close"} - mapping.keys()
    if missing:
        raise ValueError(
            f"CSV mist kolommen voor {sorted(missing)}. Gevonden header: {header}"
        )
    return mapping


def _parse_ts(raw: str) -> datetime:
    raw = raw.strip()
    # TradingView exporteert vaak unix seconden.
    try:
        seconds = float(raw)
        if seconds > 1e11:  # milliseconden
            seconds /= 1000.0
        return datetime.fromtimestamp(seconds, tz=timezone.utc)
    except ValueError:
        pass
    text = raw.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(text)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def load_csv(path: str | Path) -> list[Bar]:
    path = Path(path)
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"{path} heeft geen header")
        cols = _resolve_columns(list(reader.fieldnames))

        bars: list[Bar] = []
        for lineno, row in enumerate(reader, start=2):
            try:
                bars.append(
                    Bar(
                        ts=_parse_ts(row[cols["ts"]]),
                        open=float(row[cols["open"]]),
                        high=float(row[cols["high"]]),
                        low=float(row[cols["low"]]),
                        close=float(row[cols["close"]]),
                        volume=float(row[cols["volume"]] or 0.0) if "volume" in cols else 0.0,
                    )
                )
            except (TypeError, ValueError) as exc:
                # Lege regels aan het eind van een export zijn normaal; stille
                # datafouten midden in de reeks zijn dat niet.
                if any((row.get(c) or "").strip() for c in cols.values()):
                    raise ValueError(f"{path}:{lineno} onleesbaar: {exc}") from exc

    bars.sort(key=lambda b: b.ts)
    if not bars:
        raise ValueError(f"{path} bevat geen bruikbare bars")
    return bars
