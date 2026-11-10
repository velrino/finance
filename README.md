# Finance Data

**TL;DR:** 2026-11-10 snapshot: USD/BRL **5.5817**, **+1.3491%** versus the previous close. Bullish 4-hour structure, with elevated pullback risk. Today's candle is partial; weekday statistics exclude it.

## Current USD/BRL snapshot

Collected at **2026-11-10T20:33:22Z**. Quote timestamp: **2026-11-10T20:33:20Z**. TradingView session: `market`. This is an intraday snapshot, not today's final close or a PTAX fixing.

| Reading | Value |
|---|---:|
| Session date / weekday | 2026-11-10 / Tuesday |
| Latest daily-candle price | 5.5817 BRL |
| Previous close | 5.5074 BRL |
| Open / high / low | 5.5078 / 5.6130 / 5.5078 |
| Change versus previous close | +1.3491% |
| Opening gap | +0.0073% |
| Daily history | 5,000 candles, 2007-09-06 to 2026-11-10 |

Daily candles, scanner readings, quotes and chart are asynchronous snapshots and can differ slightly. Scanner values have their own fields in the JSON; do not substitute them for the candle close.

## Today's historical comparison

Today is **Tuesday**. Monday statistics remain available for research, but are not today's weekday signal.

| Completed sessions | Count | Up | Down | Mean return | Median return |
|---|---:|---:|---:|---:|---:|
| Tuesday | 998 | 46.69% | 51.80% | -0.0517% | -0.0327% |
| Monday | 1001 | 52.35% | 45.85% | +0.1045% | +0.0330% |

Returns compare each session's close with the previous trading close. Flat sessions explain any gap to 100%. Historical frequencies are descriptive, not a calibrated probability for today's close; no predictive edge or trading strategy has been validated.

## Updated 4-hour context

![USD/BRL 4-hour candles, standard EMAs and RSI](trading-view/USDBRL.png)

The chart is generated from the refreshed TradingView candles, not a TradingView screenshot. Its latest candle may be partial.

| Indicator | Reading |
|---|---:|
| Standard 4h EMA50 | 5.4515 |
| Standard 4h EMA100 | 5.3535 |
| Wilder RSI14 | 76.49 |

**Interpretation:** bullish 4-hour structure, with elevated pullback risk. RSI is above 70: momentum is strong, but overbought conditions can persist and do not confirm a reversal. The EMA band is a trend reference, not guaranteed support. A loss of the band would weaken the current structure. This snapshot does not justify a personalized sell or hold decision.

### Legacy CA_MA

[The original Pine script](script/ca-ma.pine) is preserved. Its August values are superseded. It smooths a mapped higher-timeframe price series, so its output is not equivalent to true weekly EMA50/100. This refresh uses explicitly labeled standard 4h indicators instead; no current legacy CA_MA value is claimed. See [TradingView's multi-timeframe documentation](https://www.tradingview.com/pine-script-docs/concepts/other-timeframes-and-data/).

## Files and refresh

- [Daily candles, quote, scanner and completed-session statistics](symbol/usd-brl.json)
- [4-hour candles and reproducible indicator readings](symbol/usd-brl-4h.json)
- [Portuguese summary](summary.txt)
- [Refresh script](script/update-usd-brl.py)

```sh
python3 -m venv /tmp/finance-venv
/tmp/finance-venv/bin/pip install -r script/requirements.txt
/tmp/finance-venv/bin/python script/update-usd-brl.py
```

The script requires a candle labeled with the current São Paulo date and fails rather than publishing stale data; weekends or feed outages may therefore block a refresh. Its internal TradingView feed is undocumented and may change. The 5,000-candle window rolls forward. `isComplete` is a conservative date-based flag; the current day's candle stays excluded even after the local close. Daily zero volume is provider data, not proof of no trading.

## Crypto research

[PLUME regulatory summary](crypto/PLUME/README.md) · [Plume versus Ondo: AI correction scenarios](crypto/PLUME/OUTLOOK.md). Research dated November 10, 2026.

## Sources and scope

[TradingView USD/BRL](https://www.tradingview.com/symbols/USDBRL/) · [4-hour chart](https://www.tradingview.com/chart/?symbol=FX_IDC%3AUSDBRL&interval=240) · [Scanner endpoint](https://scanner.tradingview.com/forex/scan).

Statistical and technical analysis only. No macroeconomic forecast, verified predictive model, or personalized investment recommendation.
