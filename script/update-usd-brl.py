#!/usr/bin/env python3
"""Refresh TradingView snapshots and reports. Requires websocket-client and matplotlib."""
import argparse
import datetime as dt
import json
from pathlib import Path
import re
import statistics
import time
import urllib.request
from zoneinfo import ZoneInfo
import websocket

ROOT = Path(__file__).resolve().parents[1]
FIELDS = ['close', 'open', 'high', 'low', 'change', 'change_abs', 'RSI|240',
          'EMA50|240', 'EMA100|240', 'Recommend.All|240', 'High.1M', 'Low.1M',
          'Perf.1M', 'Perf.3M', 'Perf.6M', 'Perf.W', 'Perf.Y', 'Perf.YTD',
          'Recommend.All', 'price_52_week_high', 'price_52_week_low']
UTC = dt.timezone.utc

def now():
    return dt.datetime.now(UTC).isoformat(timespec='seconds').replace('+00:00', 'Z')

def fetch():
    ws = websocket.create_connection('wss://data.tradingview.com/socket.io/websocket',
                                    origin='https://www.tradingview.com', timeout=25)
    def send(method, params):
        data = json.dumps({'m': method, 'p': params}, separators=(',', ':'))
        ws.send(f'~m~{len(data)}~m~{data}')
    out = {'series': {}, 'quote': {}}
    try:
        send('set_auth_token', ['unauthorized_user_token'])
        for session, interval, count in [('cs_finance_daily', '1D', 5000), ('cs_finance_h4', '240', 1200)]:
            send('chart_create_session', [session, ''])
            send('resolve_symbol', [session, 'symbol_1', '={"symbol":"FX_IDC:USDBRL","adjustment":"splits","session":"regular"}'])
            send('create_series', [session, 's1', 's1', 'symbol_1', interval, count])
        send('quote_create_session', ['qs_finance'])
        send('quote_set_fields', ['qs_finance', 'lp', 'lp_time', 'ch', 'chp', 'prev_close_price',
                                 'open_price', 'high_price', 'low_price', 'current_session',
                                 'currency_code', 'exchange', 'description', 'type', 'update_mode', 'volume'])
        send('quote_add_symbols', ['qs_finance', 'FX_IDC:USDBRL'])
        done = set()
        deadline = time.monotonic() + 65
        while time.monotonic() < deadline:
            for chunk in re.split(r'~m~\d+~m~', ws.recv()):
                if chunk.startswith('~h~'):
                    ws.send(f'~m~{len(chunk)}~m~{chunk}')
                    continue
                try:
                    message = json.loads(chunk)
                except ValueError:
                    continue
                method, params = message.get('m'), message.get('p', [])
                if method == 'timescale_update':
                    for value in params[1].values():
                        if isinstance(value, dict) and 's' in value:
                            out['series'][params[0]] = value['s']
                elif method == 'qsd' and params[1].get('s') == 'ok':
                    out['quote'].update(params[1].get('v', {}))
                elif method == 'series_completed':
                    done.add(params[0])
                elif method and 'error' in method:
                    raise RuntimeError(str(message))
            if len(done) == 2 and out['quote'].get('lp'):
                break
        if len(done) != 2 or not out['quote'].get('lp'):
            raise RuntimeError('Incomplete TradingView response; files were not updated.')
    finally:
        ws.close()
    return out

def stats(rows, field):
    values = [r[field] for r in rows if r[field] is not None]
    if not values:
        return {'count': 0}
    return dict(count=len(values), average=round(statistics.mean(values), 6),
                median=round(statistics.median(values), 6), min=min(values), max=max(values),
                positiveCount=sum(v > 0 for v in values), negativeCount=sum(v < 0 for v in values),
                flatCount=sum(v == 0 for v in values), positiveRate=round(sum(v > 0 for v in values)/len(values), 4))

def enrich(raw, daily):
    rows = []
    previous = None
    today = dt.datetime.now(ZoneInfo('America/Sao_Paulo')).date().isoformat()
    for item in raw:
        timestamp, o, h, l, c, volume = item['v'][:6]
        # FX_IDC daily sessions start at 22:00 UTC on the preceding calendar date.
        label = dt.datetime.fromtimestamp(timestamp, UTC) + (dt.timedelta(hours=12) if daily else dt.timedelta())
        day = label.date().isoformat()
        pct = lambda a, b: round((a/b-1)*100, 6) if b else None
        rows.append(dict(date=day, weekday=label.strftime('%A'), timestamp=int(timestamp),
                         open=o, high=h, low=l, close=c, volume=volume, previousClose=previous,
                         closeToCloseChange=round(c-previous, 6) if previous else None,
                         closeToCloseChangePct=pct(c, previous), openToCloseChange=round(c-o, 6),
                         openToCloseChangePct=pct(c, o), rangePct=round((h-l)/l*100, 6),
                         gapFromPreviousClosePct=pct(o, previous), isMonday=label.weekday() == 0,
                         isComplete=day < today if daily else timestamp + 4*3600 <= time.time()))
        if not (0 < l <= min(o, c) <= max(o, c) <= h):
            raise ValueError(f'Invalid OHLC: {day}')
        previous = c
    assert rows and len({r['timestamp'] for r in rows}) == len(rows)
    assert all(a['timestamp'] < b['timestamp'] for a, b in zip(rows, rows[1:]))
    if daily and rows[-1]['date'] != today:
        raise RuntimeError(f"Latest candle is {rows[-1]['date']}, expected {today}; refusing stale refresh.")
    return rows

def write_json(path, value):
    (ROOT/path).write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False)+'\n')

def chart(rows, generated):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    closes = [r['close'] for r in rows]
    def ema(period):
        values = [closes[0]]
        for c in closes[1:]: values.append(values[-1] + 2/(period+1)*(c-values[-1]))
        return values
    rsi = [float('nan')]*len(closes)
    gains = [max(b-a, 0) for a,b in zip(closes, closes[1:])]
    losses = [max(a-b, 0) for a,b in zip(closes, closes[1:])]
    gain, loss = statistics.mean(gains[:14]), statistics.mean(losses[:14])
    for i in range(14, len(closes)):
        if i > 14: gain,loss = (gain*13+gains[i-1])/14, (loss*13+losses[i-1])/14
        rsi[i] = 100 - 100/(1+gain/loss) if loss else (100 if gain else 50)
    start = max(0, len(rows)-150)
    plt.style.use('dark_background')
    fig, (ax, momentum) = plt.subplots(2,1, figsize=(14,8), sharex=True, gridspec_kw={'height_ratios':[3,1]})
    for i,r in enumerate(rows[start:]):
        color = '#39c5a3' if r['close'] >= r['open'] else '#f27878'
        ax.vlines(i,r['low'],r['high'],color=color,linewidth=.8)
        ax.add_patch(Rectangle((i-.3,min(r['open'],r['close'])),.6,max(abs(r['close']-r['open']),.0001),color=color))
    for period,color in [(50,'#f4c56a'),(100,'#8aafff')]: ax.plot(ema(period)[start:],label=f'4h EMA {period}',color=color)
    ax.set_title(f'USD/BRL | FX_IDC | 4 hours | {generated}\nLatest candle may be partial; standard EMAs, not legacy CA_MA',loc='left')
    ax.set_ylabel('BRL per USD');ax.legend();ax.grid(alpha=.15)
    momentum.plot(rsi[start:], color='#ba9cff',label='RSI 14 (Wilder)')
    for level in [30,50,70]:momentum.axhline(level,color='gray',alpha=.5,linewidth=.7)
    momentum.set_ylim(0,100);momentum.legend();momentum.grid(alpha=.15)
    ticks=list(range(0,len(rows)-start,20));momentum.set_xticks(ticks,[rows[start+i]['date'] for i in ticks],rotation=20)
    momentum.set_xlabel('UTC candle dates; equal spacing excludes market closures')
    fig.tight_layout();fig.savefig(ROOT/'trading-view/USDBRL.png',dpi=140);plt.close(fig)
    return {'EMA50':round(ema(50)[-1],6),'EMA100':round(ema(100)[-1],6),'RSI14':round(rsi[-1],6)}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--raw',type=Path);parser.add_argument('--scanner',type=Path)
    args=parser.parse_args()
    raw=json.loads(args.raw.read_text()) if args.raw else fetch()
    collected=now()
    if args.scanner:
        scanner=json.loads(args.scanner.read_text())
    else:
        request=urllib.request.Request('https://scanner.tradingview.com/forex/scan',
             data=json.dumps({'symbols':{'tickers':['FX_IDC:USDBRL']},'columns':FIELDS}).encode(),
             headers={'Content-Type':'application/json','User-Agent':'Mozilla/5.0'})
        with urllib.request.urlopen(request,timeout=25) as response: scanner=json.load(response)
    scanner_collected = dt.datetime.fromtimestamp(args.scanner.stat().st_mtime, UTC).isoformat(timespec='seconds').replace('+00:00', 'Z') if args.scanner else now()
    assert scanner['data'][0]['s']=='FX_IDC:USDBRL' and len(scanner['data'][0]['d'])==len(FIELDS)
    daily=enrich(raw['series']['cs_finance_daily'],True);h4=enrich(raw['series']['cs_finance_h4'],False)
    q=raw['quote'];last=daily[-1];previous=daily[-2]
    quote=dict(proName='FX_IDC:USDBRL',shortName='USDBRL',description=q.get('description'),exchange=q.get('exchange'),
               type=q.get('type'),currencyCode=q.get('currency_code'),lastPrice=q['lp'],change=q['ch'],changePercent=q['chp'],
               currentSession=q.get('current_session'),lastPriceTime=dt.datetime.fromtimestamp(q['lp_time'],UTC).isoformat().replace('+00:00','Z'),
               updateMode=q.get('update_mode'),volume=q.get('volume'))
    fields=['closeToCloseChangePct','openToCloseChangePct','gapFromPreviousClosePct','rangePct']
    complete=[r for r in daily if r['isComplete']]
    weekdays=[]
    for day in ['Monday','Tuesday','Wednesday','Thursday','Friday']:
        rows=[r for r in complete if r['weekday']==day]
        weekdays.append(dict(weekday=day,bars=len(rows),**{f:stats(rows,f) for f in fields}))
    mondays=[r for r in complete if r['isMonday']]
    pattern=dict(definition='Completed Monday candles only; returns versus previous trading close and session open.',
                 bars=len(mondays),firstMonday=mondays[0]['date'],lastMonday=mondays[-1]['date'],
                 **{f:stats(mondays,f) for f in fields[:3]},last12Mondays=mondays[-12:])
    source=dict(name='TradingView chart websocket',chartUrl='https://www.tradingview.com/chart/?symbol=FX_IDC%3AUSDBRL',
                transport='wss://data.tradingview.com/socket.io/websocket',
                note='Undocumented feed; analysis snapshot. Daily dates label the session ending on that date (22:00 UTC start on preceding date).',
                statisticsPolicy='Exclude the current daily candle from all weekday and Monday statistics.')
    indicators=chart(h4,collected)
    write_json(Path('symbol/usd-brl.json'),dict(symbol='FX_IDC:USDBRL',displaySymbol='USD/BRL',description=q.get('description'),
        interval='1D',generatedAt=collected,source=source,requestedBars=5000,barCount=len(daily),firstDate=daily[0]['date'],
        lastDate=last['date'],quoteSnapshot=quote,tradingViewScannerSnapshot=dict(zip(FIELDS,scanner['data'][0]['d'])),
        scannerCollectedAt=scanner_collected,mondayPattern=pattern,weekdayStats=weekdays,history=daily))
    write_json(Path('symbol/usd-brl-4h.json'),dict(symbol='FX_IDC:USDBRL',interval='240',generatedAt=collected,
        source=source,barCount=len(h4),indicators=indicators,
        calculation='Standard EMA50/100 and Wilder RSI14 on 4h closes, seeded from this 1200-bar window. Includes partial latest bar. Not legacy CA_MA.',history=h4))
    todaystats=next(r for r in weekdays if r['weekday']==last['weekday'])
    s=todaystats['closeToCloseChangePct'];m=pattern['closeToCloseChangePct']
    bullish=last['close']>indicators['EMA50']>indicators['EMA100']
    bias='Bullish 4-hour structure, with elevated pullback risk' if bullish else 'Mixed 4-hour structure; no strong directional conclusion'
    rsi=indicators['RSI14']
    report=f'''# Finance Data

**TL;DR:** {last['date']} snapshot: USD/BRL **{last['close']:.4f}**, **{last['closeToCloseChangePct']:+.4f}%** versus the previous close. {bias}. Today's candle is partial; weekday statistics exclude it.

## Current USD/BRL snapshot

Collected at **{collected}**. Quote timestamp: **{quote['lastPriceTime']}**. TradingView session: `{quote['currentSession']}`. This is an intraday snapshot, not today's final close or a PTAX fixing.

| Reading | Value |
|---|---:|
| Session date / weekday | {last['date']} / {last['weekday']} |
| Latest daily-candle price | {last['close']:.4f} BRL |
| Previous close | {previous['close']:.4f} BRL |
| Open / high / low | {last['open']:.4f} / {last['high']:.4f} / {last['low']:.4f} |
| Change versus previous close | {last['closeToCloseChangePct']:+.4f}% |
| Opening gap | {last['gapFromPreviousClosePct']:+.4f}% |
| Daily history | {len(daily):,} candles, {daily[0]['date']} to {last['date']} |

Daily candles, scanner readings, quotes and chart are asynchronous snapshots and can differ slightly. Scanner values have their own fields in the JSON; do not substitute them for the candle close.

## Today's historical comparison

Today is **{last['weekday']}**. Monday statistics remain available for research, but are not today's weekday signal.

| Completed sessions | Count | Up | Down | Mean return | Median return |
|---|---:|---:|---:|---:|---:|
| {last['weekday']} | {s['count']} | {100*s['positiveCount']/s['count']:.2f}% | {100*s['negativeCount']/s['count']:.2f}% | {s['average']:+.4f}% | {s['median']:+.4f}% |
| Monday | {m['count']} | {100*m['positiveCount']/m['count']:.2f}% | {100*m['negativeCount']/m['count']:.2f}% | {m['average']:+.4f}% | {m['median']:+.4f}% |

Returns compare each session's close with the previous trading close. Flat sessions explain any gap to 100%. Historical frequencies are descriptive, not a calibrated probability for today's close; no predictive edge or trading strategy has been validated.

## Updated 4-hour context

![USD/BRL 4-hour candles, standard EMAs and RSI](trading-view/USDBRL.png)

The chart is generated from the refreshed TradingView candles, not a TradingView screenshot. Its latest candle may be partial.

| Indicator | Reading |
|---|---:|
| Standard 4h EMA50 | {indicators['EMA50']:.4f} |
| Standard 4h EMA100 | {indicators['EMA100']:.4f} |
| Wilder RSI14 | {rsi:.2f} |

**Interpretation:** {bias.lower()}. {'RSI is above 70: momentum is strong, but overbought conditions can persist and do not confirm a reversal.' if rsi>70 else 'RSI alone does not establish the next direction.'} The EMA band is a trend reference, not guaranteed support. A loss of the band would weaken the current structure. This snapshot does not justify a personalized sell or hold decision.

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
'''
    (ROOT/'README.md').write_text(report)
    (ROOT/'summary.txt').write_text(f'''USD/BRL — {last['date']} — coleta {collected}

TL;DR: dólar a R$ {last['close']:.4f}, variação de {last['closeToCloseChangePct']:+.4f}% contra o fechamento anterior. Candle diário ainda parcial.

Leitura: {'estrutura de alta no gráfico de 4 horas' if bullish else 'estrutura mista no gráfico de 4 horas'}. EMA50: {indicators['EMA50']:.4f}; EMA100: {indicators['EMA100']:.4f}; RSI14: {rsi:.2f}.
{'RSI acima de 70 indica sobrecompra, mas não confirma reversão. Há risco de realização após a alta.' if rsi>70 else 'Os indicadores não garantem a direção da próxima sessão.'}

Dia da semana: {last['weekday']}. Estatísticas apenas de sessões completas desse dia: {s['count']}, alta em {100*s['positiveCount']/s['count']:.2f}%, retorno mediano {s['median']:+.4f}%. Frequências históricas não são uma previsão validada.

Os níveis e conclusões de agosto foram substituídos. Não há base personalizada para determinar quanto realizar ou manter. Fontes, metodologia e dados: README.md e symbol/.
''')
    print(json.dumps(dict(collectedAt=collected,last=last,indicators=indicators,completedWeekday=todaystats),indent=2))

if __name__ == '__main__':
    main()
