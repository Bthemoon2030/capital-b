#!/usr/bin/env python3
"""Paper-trading runner tegen Alpaca.

Ontwerpuitgangspunten, in volgorde van belang:

1. PAPER ONLY. Deze runner weigert te draaien tegen een niet-paper endpoint.
   Live handelen vraagt om een bewuste, aparte beslissing van jou, niet om
   een vlaggetje omzetten.
2. Dry-run is de default. Zonder --execute wordt er niets verstuurd.
3. Sleutels komen uitsluitend uit environment variables. Zet ze nooit in dit
   repo; .env staat in .gitignore.
4. Elke beslissing gaat naar het journaal, ook als er niet gehandeld wordt.
   Wat je niet logt kun je later niet evalueren.

Draai hem periodiek (cron / GitHub Actions), niet als eeuwige loop: dit
proces mag omvallen zonder dat er iets kapotgaat.

    python3 live/alpaca_paper.py                 # dry run
    python3 live/alpaca_paper.py --execute       # stuurt echte paper-orders
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from data.alpaca_loader import fetch_bars  # noqa: E402
from strategies.sma_cross import SmaCross  # noqa: E402

PAPER_BASE = "https://paper-api.alpaca.markets"
JOURNAL = Path(__file__).resolve().parent.parent / "journal" / "paper_trades.jsonl"


class AlpacaPaper:
    def __init__(self, base_url: str = PAPER_BASE) -> None:
        if "paper-api" not in base_url:
            raise RuntimeError(
                f"Weigering: {base_url} is geen paper-endpoint. Deze runner "
                "handelt uitsluitend op papier."
            )
        self.base_url = base_url.rstrip("/")

        key = os.environ.get("ALPACA_API_KEY_ID")
        secret = os.environ.get("ALPACA_API_SECRET_KEY")
        if not key or not secret:
            raise RuntimeError(
                "ALPACA_API_KEY_ID en ALPACA_API_SECRET_KEY ontbreken in de "
                "environment. Zie trading/.env.example."
            )
        self.headers = {
            "APCA-API-KEY-ID": key,
            "APCA-API-SECRET-KEY": secret,
            "Content-Type": "application/json",
        }

    def _request(self, method: str, path: str, body: dict | None = None) -> dict:
        data = json.dumps(body).encode() if body else None
        request = urllib.request.Request(
            f"{self.base_url}{path}", data=data, headers=self.headers, method=method
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                raw = response.read().decode()
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode(errors="replace")
            raise RuntimeError(f"Alpaca {method} {path} -> {exc.code}: {detail}") from exc

    def account(self) -> dict:
        return self._request("GET", "/v2/account")

    def position(self, symbol: str) -> dict | None:
        # Alpaca gebruikt in het positie-pad geen slash: BTC/USD -> BTCUSD.
        try:
            return self._request("GET", f"/v2/positions/{symbol.replace('/', '')}")
        except RuntimeError as exc:
            if "404" in str(exc):
                return None  # geen positie is een geldige uitkomst
            raise

    def submit_market_order(self, symbol: str, notional: float, side: str) -> dict:
        return self._request(
            "POST",
            "/v2/orders",
            {
                "symbol": symbol,
                "notional": round(abs(notional), 2),
                "side": side,
                "type": "market",
                "time_in_force": "gtc",
            },
        )


def log(entry: dict) -> None:
    JOURNAL.parent.mkdir(parents=True, exist_ok=True)
    entry["logged_at"] = datetime.now(timezone.utc).isoformat()
    with JOURNAL.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry) + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Paper trade BTC via Alpaca")
    parser.add_argument("--symbol", default="BTC/USD")
    parser.add_argument("--timeframe", default="1d", choices=["1h", "4h", "1d"])
    parser.add_argument("--fast", type=int, default=20)
    parser.add_argument("--slow", type=int, default=50)
    parser.add_argument("--max-weight", type=float, default=0.5,
                        help="Hoogste deel van het account in BTC. Default 50%%.")
    parser.add_argument("--threshold", type=float, default=0.05,
                        help="Kleiner verschil met het doelgewicht = niet handelen")
    parser.add_argument("--execute", action="store_true",
                        help="Zonder deze vlag wordt er niets verstuurd")
    args = parser.parse_args(argv)

    broker = AlpacaPaper()
    account = broker.account()
    equity = float(account["equity"])

    strategy = SmaCross(args.fast, args.slow)
    bars = fetch_bars(symbol=args.symbol, timeframe=args.timeframe)
    if len(bars) <= strategy.warmup:
        print(f"Te weinig historie ({len(bars)} bars, {strategy.warmup} nodig)")
        return 1

    # De laatste bar kan nog open staan; beslis op de laatste GESLOTEN bar,
    # net als in de backtest.
    closed = bars[:-1]
    raw_target = strategy.on_bar(closed[-1], closed)
    target_weight = min(raw_target, args.max_weight)

    position = broker.position(args.symbol)
    current_value = float(position["market_value"]) if position else 0.0
    current_weight = current_value / equity if equity > 0 else 0.0
    delta_value = (target_weight * equity) - current_value

    decision = {
        "ts": closed[-1].ts.isoformat(),
        "symbol": args.symbol,
        "strategy": strategy.describe(),
        "last_close": closed[-1].close,
        "equity": equity,
        "current_weight": round(current_weight, 4),
        "target_weight": round(target_weight, 4),
        "delta_value": round(delta_value, 2),
        "executed": False,
    }

    print(f"Account equity   USD {equity:,.2f}")
    print(f"Laatste close    {closed[-1].close:,.2f} ({closed[-1].ts.date()})")
    print(f"Huidig gewicht   {current_weight:.1%}")
    print(f"Doelgewicht      {target_weight:.1%}")

    if abs(target_weight - current_weight) < args.threshold:
        decision["action"] = "hold"
        print("-> binnen de bandbreedte, geen order")
    elif abs(delta_value) < 1.0:
        decision["action"] = "too_small"
        print("-> order te klein om te versturen")
    else:
        side = "buy" if delta_value > 0 else "sell"
        decision["action"] = side
        if args.execute:
            order = broker.submit_market_order(args.symbol, delta_value, side)
            decision["executed"] = True
            decision["order_id"] = order.get("id")
            print(f"-> {side.upper()} USD {abs(delta_value):,.2f} verstuurd (id {order.get('id')})")
        else:
            print(f"-> zou {side.upper()} USD {abs(delta_value):,.2f} doen (dry run, --execute om te versturen)")

    log(decision)
    print(f"\nGelogd in {JOURNAL}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
