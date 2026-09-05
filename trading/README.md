# Trading — backtest- en paper-engine

Systematisch BTC handelen, opgebouwd in de volgorde die de fouten goedkoop houdt:
eerst regels opschrijven, dan backtesten met eerlijke kosten, dan paper traden,
en pas daarna praten over echt geld.

Geen dependencies. Alleen Python 3.11+ en de standard library, zodat dit op een
laptop, een VPS of een GitHub Actions runner draait zonder installatiegedoe.

## Rolverdeling

| Wie | Wat |
| --- | --- |
| Claude | strategie, backtest, risicologica, code review |
| De bot | draait periodiek op jouw machine of in Actions |
| Jij | houdt de API-sleutels, en drukt op de knop |

Claude draait niet continu en heeft geen geheugen tussen sessies. Alles wat
onthouden moet worden staat daarom in dit repo, niet in een gesprek.

## Snel starten

```bash
cd trading
python3 selftest.py                  # verifieert de engine, geen data of internet nodig
python3 run_backtest.py --synthetic  # demo op synthetische data
```

Met echte data:

```bash
# Optie A: TradingView-export (chart -> Export chart data -> CSV)
python3 run_backtest.py --csv data/btc_1d.csv --timeframe 1d

# Optie B: rechtstreeks bij Alpaca ophalen
python3 data/alpaca_loader.py 1d data/btc_1d.csv
python3 run_backtest.py --csv data/btc_1d.csv --timeframe 1d --show-costless
```

Paper traden:

```bash
cp .env.example .env      # vul je PAPER-sleutels in
set -a && . ./.env && set +a
python3 live/alpaca_paper.py              # dry run, verstuurt niets
python3 live/alpaca_paper.py --execute    # verstuurt paper-orders
```

## Wat er bewust in zit

**Geen lookahead.** Een signaal wordt berekend op de close van bar `i` en
uitgevoerd op de open van bar `i+1`. Dit kost rendement op papier en is de
reden dat het cijfer iets waard is.

**Kosten staan vooraan.** Default 25 bps fee + 5 bps slippage per kant, dus
60 bps per round trip. Op EUR 1000 is dat geen detail: een strategie die
dagelijks omdraait betaalt meer dan de helft van het kapitaal per jaar aan
kosten. `--show-costless` laat zien hoeveel van je rendement puur kosten was.

**Buy-and-hold als benchmark.** Elke backtest rapporteert automatisch naast
simpelweg kopen en niets doen. Voor BTC is dat een hoge lat, en een strategie
die hem niet haalt is geen strategie maar duur bijgeloof.

**Long-only, geen leverage.** Bewust beperkt. Leverage en shorts verbergen
fouten in de strategie achter grotere getallen.

**Paper-only guard.** `live/alpaca_paper.py` weigert te draaien tegen een
niet-paper endpoint, en verstuurt zonder `--execute` niets. Live gaan moet een
bewuste, aparte beslissing zijn.

**Alles wordt gelogd.** Elke beslissing gaat naar `journal/paper_trades.jsonl`,
ook als er niet gehandeld wordt. Wat je niet logt, kun je later niet evalueren.

## Wat dit NIET is

- **Geen beleggingsadvies.** Dit is gereedschap, geen aanbeveling.
- **`strategies/sma_cross.py` is geen strategie-voorstel.** Het is de simpelste
  referentie-implementatie om de pijplijn aantoonbaar te laten werken. MA-crossovers
  op BTC zijn breed bekend en de edge is grotendeels weg. Verwacht dat hij na
  kosten verliest van buy-and-hold — dat hoort een eerlijke backtest te laten zien.
- **Synthetische data zegt niets** over een strategie. Een random walk mist alles
  wat BTC interessant maakt: volatiliteitsclusters, fat tails, regimes. Het bestaat
  alleen om de engine te testen.

## Nog niet gedaan / opletten

- De Alpaca-endpoints zijn geschreven zonder netwerktoegang en dus **niet live
  getest**. Controleer ze tegen de actuele docs; de crypto-API is al eens
  geversied (v1beta1 -> v1beta3).
- Alpaca crypto is niet in elk rechtsgebied beschikbaar voor een *funded* account.
  Voor paper is dat doorgaans geen probleem, maar check het voordat je verder plant.
- Geen walk-forward validatie. Zonder out-of-sample test is elke geoptimaliseerde
  parameter een vorm van curve fitting.
- Nog geen echte strategie. Dat is het volgende gesprek, en het enige deel dat
  er uiteindelijk toe doet.
