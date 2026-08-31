# Finance Data

This repository currently stores a USD/BRL historical analysis snapshot at:

```text
symbol/usd-brl.json
```

## USD/BRL Dataset

The `symbol/usd-brl.json` file contains daily USD/BRL candles for `FX_IDC:USDBRL`.
It was generated on `2026-08-31T10:26:50Z` from TradingView's chart websocket.

The snapshot includes:

- `5000` daily candles
- Date range from `2007-06-27` to `2026-08-31`
- Daily `open`, `high`, `low`, `close`, and `volume`
- Computed weekday fields such as `weekday` and `isMonday`
- Computed return fields:
  - `closeToCloseChangePct`
  - `openToCloseChangePct`
  - `gapFromPreviousClosePct`
  - `rangePct`
- Aggregated weekday statistics in `weekdayStats`
- A focused Monday analysis summary in `mondayPattern`
- The last 12 Monday records in `mondayPattern.last12Mondays`

## Monday Pattern Summary

The Monday pattern is measured in two ways:

- `closeToCloseChangePct`: Monday close compared with the previous trading day's close.
- `openToCloseChangePct`: Monday close compared with Monday open.

Current Monday summary:

```json
{
  "mondayBars": 1001,
  "averageCloseToCloseChangePct": 0.098448,
  "medianCloseToCloseChangePct": 0.036303,
  "positiveRate": 0.5225
}
```

## Today's Bias — August 31, 2026

**Conclusion:** the bias for today's close is **neutral to slightly bearish, with low confidence**. The historical pattern that most closely resembles today's opening conditions favors a decline by a small margin, while the complete set of Mondays has a slightly bullish bias. Therefore, the historical data does not support a strong prediction in either direction.

The comparison below uses the previous `1000` completed Mondays and excludes today's partial candle. In this snapshot, USD/BRL was trading at `5.1838`, down `0.0231%` from the previous close of `5.1850`.

| Evidence | Historical result or today's reading | Signal | Interpretation |
|---|---:|:---:|---|
| All completed Mondays | Up in `52.30%`, down in `45.90%`; mean return of `+0.0986%` and median return of `+0.0365%` | Slightly bullish | There is a small historical advantage for an upward move, but `52.30%` is close to a random outcome. |
| Monday after a positive previous session | `496` cases; up in `49.40%`, down in `49.60%`; median return of `0.0000%` | Neutral | Friday's `+0.4436%` gain does not, by itself, create reliable continuation on Monday. |
| Monday with no opening gap | `570` cases; up in `48.25%`, down in `49.47%`; median return of `0.0000%` | Neutral/slightly bearish | Today's opening gap was `0.0000%`. Opening without a gap is common (`57.00%` of Mondays) and does not provide a strong directional signal. |
| Monday with no gap after a positive session — the closest match to today | `283` cases; up in `47.00%`, down in `51.94%`; mean return of `+0.0335%` and median return of `-0.0592%` | Slightly bearish | Both the majority of outcomes and the median favor a decline, but the difference is small and the mean remains positive because of larger upward moves. |
| Today's move versus the previous close | `-0.0231%`, at the `44.7th` percentile of historical Mondays | Slightly bearish | Trading below both the opening price and the previous close favors a decline at this point, but the move is normal and very small. |
| Today's candle range | `0.0231%`, versus a historical median of `1.1461%`; `0.9th` percentile | Inconclusive | This is the main difference from the historical pattern and is explained by the candle still being in progress. It should not be interpreted as low volatility for the entire day. |

### Is Today's Behavior Different?

In terms of direction, **no**: today's small decline is near the center of the historical distribution and is not unusual. The absence of an opening gap also matches the most common Monday behavior. The only meaningful difference is the extremely narrow range, but this is primarily due to the snapshot time and may disappear as the session progresses.

This outlook is exclusively statistical and technical and is based on the local dataset. It does not incorporate news, interest rates, currency flows, or the day's macroeconomic events, and it is not financial advice.

## Source Note

TradingView loads candle history through an internal, undocumented chart feed.
This dataset should be treated as an analysis snapshot, not as a stable production API integration.
