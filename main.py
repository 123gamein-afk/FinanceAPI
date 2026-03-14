from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
import yfinance as yf
import asyncio
from datetime import datetime
import random
import pandas as pd

app = FastAPI(
    title="Indian Stock API - Real + Simulation (Full Version)",
    description="REST + Real Native WebSocket + Indian Market Simulation 24/7"
)

# ==================== HELPERS ====================
def normalize_indian(t: str) -> str:
    t = t.upper().strip()
    if not t.endswith(('.NS', '.BO')) and not t.startswith('^'):
        t += '.NS'
    return t

def normalize_foreign(t: str) -> str:
    return t.upper().strip()

# ==================== REST ENDPOINTS ====================
@app.get("/info/{ticker}")
def get_stock_info(ticker: str):
    ticker = normalize_indian(ticker)
    try:
        info = yf.Ticker(ticker).info
        return {**info, "symbol": ticker}
    except Exception as e:
        return {"error": str(e)}

@app.get("/history/{ticker}")
def get_history(
    ticker: str,
    period: str = Query("1y", description="Valid: 1d,5d,1mo,3mo,6mo,1y,2y,5y,10y,ytd,max"),
    interval: str = Query("1d", description="Valid: 1m,2m,5m,15m,30m,60m,90m,1h,1d,5d,1wk,1mo,3mo"),
    start: str = Query(None, description="Start date YYYY-MM-DD"),
    end: str = Query(None, description="End date YYYY-MM-DD")
):
    """Fixed for yfinance 2.x + full validation + graph-ready data + start/end support for scrolling"""
    
    # === FULL VALIDATION (blocks bad combos early) ===
    valid_periods = {"1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"}
    valid_intervals = {"1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h", "1d", "5d", "1wk", "1mo", "3mo"}
    
    if not start or not end:
        if period not in valid_periods:
            return {"error": f"Invalid period '{period}'. Valid: {sorted(valid_periods)}"}
    if interval not in valid_intervals:
        return {"error": f"Invalid interval '{interval}'. Valid: {sorted(valid_intervals)}"}
    
    # Combo rules (prevents empty data)
    intraday = {"1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h"}
    if interval in intraday:
        if period not in {"1d", "5d", "1mo"} and not (start and end):
            return {"error": f"Intraday interval '{interval}' only works with period=1d, 5d or 1mo, or with start/end dates"}
        if interval == "1m" and period not in {"1d", "5d"} and not (start and end):
            return {"error": "1m interval ONLY supports period=1d or 5d, or start/end dates"}

    ticker = normalize_indian(ticker)
    try:
        if start and end:
            df = yf.download(
                ticker,
                start=start,
                end=end,
                interval=interval,
                progress=False,
                auto_adjust=True,
                prepost=True
            )
        else:
            df = yf.download(
                ticker,
                period=period,
                interval=interval,
                progress=False,
                auto_adjust=True,
                prepost=True
            )
        
        if df.empty:
            return {"error": "No data found for this ticker/period/interval combo"}

        # 🔥 yfinance 2.x MULTIINDEX FIX
        if isinstance(df.columns, pd.MultiIndex):
            df = df.droplevel(1, axis=1)   # removes ticker name from columns

        df = df.reset_index()

        # Handle both 'Date' (daily) and 'Datetime' (intraday)
        if "Datetime" in df.columns:
            df = df.rename(columns={"Datetime": "Date"})
        elif "Date" not in df.columns:
            df["Date"] = pd.to_datetime(df.index)

        df['Date'] = df['Date'].dt.strftime('%Y-%m-%d %H:%M:%S')

        return df.to_dict(orient="records")
    
    except Exception as e:
        return {"error": str(e)}

@app.get("/foreign/info/{ticker}")
def get_foreign_info(ticker: str):
    ticker = normalize_foreign(ticker)
    try:
        info = yf.Ticker(ticker).info
        return {**info, "symbol": ticker}
    except Exception as e:
        return {"error": str(e)}

@app.get("/foreign/history/{ticker}")
def get_foreign_history(
    ticker: str,
    period: str = Query("1y", description="Valid: 1d,5d,1mo,3mo,6mo,1y,2y,5y,10y,ytd,max"),
    interval: str = Query("1d", description="Valid: 1m,2m,5m,15m,30m,60m,90m,1h,1d,5d,1wk,1mo,3mo"),
    start: str = Query(None, description="Start date YYYY-MM-DD"),
    end: str = Query(None, description="End date YYYY-MM-DD")
):
    """Same as above but for foreign tickers (AAPL, TSLA, etc.)"""
    
    # === SAME VALIDATION (copy-pasted for consistency) ===
    valid_periods = {"1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"}
    valid_intervals = {"1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h", "1d", "5d", "1wk", "1mo", "3mo"}
    
    if not start or not end:
        if period not in valid_periods:
            return {"error": f"Invalid period '{period}'. Valid: {sorted(valid_periods)}"}
    if interval not in valid_intervals:
        return {"error": f"Invalid interval '{interval}'. Valid: {sorted(valid_intervals)}"}
    
    intraday = {"1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h"}
    if interval in intraday:
        if period not in {"1d", "5d", "1mo"} and not (start and end):
            return {"error": f"Intraday interval '{interval}' only works with period=1d, 5d or 1mo, or with start/end dates"}
        if interval == "1m" and period not in {"1d", "5d"} and not (start and end):
            return {"error": "1m interval ONLY supports period=1d or 5d, or start/end dates"}

    ticker = normalize_foreign(ticker)
    try:
        if start and end:
            df = yf.download(
                ticker,
                start=start,
                end=end,
                interval=interval,
                progress=False,
                auto_adjust=True,
                prepost=True
            )
        else:
            df = yf.download(
                ticker,
                period=period,
                interval=interval,
                progress=False,
                auto_adjust=True,
                prepost=True
            )
        
        if df.empty:
            return {"error": "No data found for this ticker/period/interval combo"}

        if isinstance(df.columns, pd.MultiIndex):
            df = df.droplevel(1, axis=1)

        df = df.reset_index()

        if "Datetime" in df.columns:
            df = df.rename(columns={"Datetime": "Date"})
        elif "Date" not in df.columns:
            df["Date"] = pd.to_datetime(df.index)

        df['Date'] = df['Date'].dt.strftime('%Y-%m-%d %H:%M:%S')

        return df.to_dict(orient="records")
    
    except Exception as e:
        return {"error": str(e)}

# ==================== REAL MULTI WEBSOCKET (Native yfinance - Instant) ====================
@app.websocket("/ws/multi")
async def websocket_multi(
    websocket: WebSocket,
    symbols: str = Query(..., description="BTC-USD,ETH-USD,RELIANCE.NS,INFY.NS etc.")
):
    await websocket.accept()
    tickers = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    print(f"✅ REAL MULTI CONNECTED: {tickers}")

    previous_closes = {}
    for t in tickers:
        try:
            previous_closes[t] = round(yf.Ticker(t).fast_info.get("previousClose") or 0, 2)
        except:
            previous_closes[t] = 0.0

    try:
        async with yf.AsyncWebSocket(verbose=False) as ws:
            await ws.subscribe(tickers)
            print(f"✅ Subscribed to real stream: {tickers}")

            def message_handler(msg: dict):
                sym = msg.get("id") or msg.get("symbol") or "unknown"
                payload = {
                    "symbol": sym,
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "lastPrice": round(msg.get("price") or 0, 2),
                    "previousClose": previous_closes.get(sym, 0),
                    "changePercent": round(msg.get("change_percent") or 0, 2),
                    "volume": msg.get("volume") or msg.get("day_volume") or 0,
                    "mode": "REAL"
                }
                asyncio.create_task(websocket.send_json(payload))

            await ws.listen(message_handler)
    except WebSocketDisconnect:
        print(f"Client disconnected (real multi): {tickers}")
    except Exception as e:
        print("Real multi error:", e)
        try:
            await websocket.send_json({"error": str(e)})
        except:
            pass

# ==================== REAL SINGLE WEBSOCKETS ====================
@app.websocket("/ws/{ticker}")
async def websocket_indian(websocket: WebSocket, ticker: str):
    await websocket.accept()
    ticker = normalize_indian(ticker)
    # Same logic as multi but single (kept short)
    try:
        previous_close = round(yf.Ticker(ticker).fast_info.get("previousClose") or 0, 2)
        async with yf.AsyncWebSocket(verbose=False) as ws:
            await ws.subscribe(ticker)
            def handler(msg):
                payload = {
                    "symbol": ticker,
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "lastPrice": round(msg.get("price") or 0, 2),
                    "previousClose": previous_close,
                    "changePercent": round(msg.get("change_percent") or 0, 2),
                    "volume": msg.get("volume") or 0,
                    "mode": "REAL"
                }
                asyncio.create_task(websocket.send_json(payload))
            await ws.listen(handler)
    except Exception as e:
        print("Indian single error:", e)

@app.websocket("/ws/foreign/{ticker}")
async def websocket_foreign(websocket: WebSocket, ticker: str):
    await websocket.accept()
    ticker = normalize_foreign(ticker)
    try:
        previous_close = round(yf.Ticker(ticker).fast_info.get("previousClose") or 0, 2)
        async with yf.AsyncWebSocket(verbose=False) as ws:
            await ws.subscribe(ticker)
            def handler(msg):
                payload = {
                    "symbol": ticker,
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "lastPrice": round(msg.get("price") or 0, 2),
                    "previousClose": previous_close,
                    "changePercent": round(msg.get("change_percent") or 0, 2),
                    "volume": msg.get("volume") or 0,
                    "mode": "REAL"
                }
                asyncio.create_task(websocket.send_json(payload))
            await ws.listen(handler)
    except Exception as e:
        print("Foreign single error:", e)

# ==================== SIMULATION (FAKE INDIAN MARKET - 24/7) ====================
@app.websocket("/ws/sim/multi")
async def websocket_sim_multi(
    websocket: WebSocket,
    symbols: str = Query(..., description="INFY,TCS,RELIANCE etc.")
):
    await websocket.accept()
    tickers = [normalize_indian(s.strip()) for s in symbols.split(",") if s.strip()]
    print(f"🧪 SIMULATION STARTED: {tickers}")

    prices = {}
    prev_closes = {}
    volumes = {}
    for t in tickers:
        try:
            fi = yf.Ticker(t).fast_info
            prices[t] = round(fi.get("lastPrice") or fi.get("previousClose") or 1000, 2)
            prev_closes[t] = round(fi.get("previousClose") or prices[t], 2)
            volumes[t] = random.randint(500000, 3000000)
        except:
            prices[t] = 1000.0
            prev_closes[t] = 1000.0
            volumes[t] = 1000000

    # First message
    for t in tickers:
        await websocket.send_json({
            "symbol": t,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "lastPrice": prices[t],
            "previousClose": prev_closes[t],
            "changePercent": 0.0,
            "volume": volumes[t],
            "mode": "SIMULATION",
            "message": "Simulation started - prices moving every 1-2 sec"
        })

    try:
        while True:
            for t in tickers:
                change = random.uniform(-4.0, 4.0)
                if random.random() < 0.12:
                    change = random.uniform(-18.0, 18.0)
                prices[t] = max(10.0, round(prices[t] + change, 2))
                chg_pct = round(((prices[t] - prev_closes[t]) / prev_closes[t]) * 100, 2)
                volumes[t] = int(volumes[t] * random.uniform(0.92, 1.08))

                payload = {
                    "symbol": t,
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "lastPrice": prices[t],
                    "previousClose": prev_closes[t],
                    "changePercent": chg_pct,
                    "volume": volumes[t],
                    "mode": "SIMULATION"
                }
                await websocket.send_json(payload)
            await asyncio.sleep(1.2)
    except WebSocketDisconnect:
        print(f"Simulation disconnected: {tickers}")
    except Exception as e:
        print("Sim error:", e)


@app.get("/graph/{ticker}")
def get_graph_data(
    ticker: str,
    period: str = Query("1mo"),
    interval: str = Query("1d"),
    start: str = Query(None),
    end: str = Query(None)
):
    """Perfect JSON for any charting library (Chart.js, Recharts, Plotly, TradingView, etc.)"""
    data = get_history(ticker, period, interval, start, end)   # reuses the fixed function
    
    if isinstance(data, dict) and "error" in data:
        return data
    
    return {
        "symbol": ticker.upper(),
        "period": period,
        "interval": interval,
        "last_updated": datetime.utcnow().isoformat() + "Z",
        "candles": data
    }

# ==================== RUN ====================
# uvicorn main:app --reload --port 8000