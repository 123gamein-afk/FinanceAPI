from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
import yfinance as yf
import asyncio
from datetime import datetime
import pandas as pd

app = FastAPI(
    title="Indian + Foreign Stock yfinance API (Native Real-Time + Multi-Symbol)",
    description="True instantaneous live streaming"
)


# ==================== HELPERS ====================

def normalize_indian(t: str) -> str:
    t = t.upper().strip()
    if not t.endswith(('.NS', '.BO')) and not t.startswith('^'):
        t += '.NS'
    return t


def normalize_foreign(t: str) -> str:
    return t.upper().strip()


# ==================== REST ENDPOINTS (unchanged) ====================

@app.get("/info/{ticker}")
def get_stock_info(ticker: str):
    ticker = normalize_indian(ticker)
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        return {**info, "symbol": ticker}
    except Exception as e:
        return {"error": str(e)}


@app.get("/history/{ticker}")
def get_history(ticker: str, period: str = Query("1y"), interval: str = Query("1d")):
    ticker = normalize_indian(ticker)
    try:
        df = yf.download(ticker, period=period, interval=interval, progress=False, auto_adjust=True)
        if df.empty: return {"error": "No data found"}
        df = df.reset_index()
        df['Date'] = df['Date'].dt.strftime('%Y-%m-%d %H:%M:%S')
        return df.to_dict(orient="records")
    except Exception as e:
        return {"error": str(e)}


@app.get("/foreign/info/{ticker}")
def get_foreign_info(ticker: str):
    ticker = normalize_foreign(ticker)
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        return {**info, "symbol": ticker}
    except Exception as e:
        return {"error": str(e)}


@app.get("/foreign/history/{ticker}")
def get_foreign_history(ticker: str, period: str = Query("1y"), interval: str = Query("1d")):
    ticker = normalize_foreign(ticker)
    try:
        df = yf.download(ticker, period=period, interval=interval, progress=False, auto_adjust=True)
        if df.empty: return {"error": "No data found"}
        df = df.reset_index()
        df['Date'] = df['Date'].dt.strftime('%Y-%m-%d %H:%M:%S')
        return df.to_dict(orient="records")
    except Exception as e:
        return {"error": str(e)}


# ==================== MULTI-SYMBOL FIRST (MUST BE BEFORE /ws/{ticker}) ====================

@app.websocket("/ws/multi")
async def websocket_multi(
        websocket: WebSocket,
        symbols: str = Query(..., description="Comma-separated: BTC-USD,ETH-USD,SOL-USD,RELIANCE.NS")
):
    await websocket.accept()
    tickers = [s.strip().upper() for s in symbols.split(",") if s.strip()]

    print(f"✅ Multi-WS subscribed to: {tickers}")  # debug in terminal

    previous_closes = {}
    for t in tickers:
        try:
            previous_closes[t] = round(yf.Ticker(t).fast_info.get("previousClose") or 0, 2)
        except:
            previous_closes[t] = 0.0

    try:
        async with yf.AsyncWebSocket(verbose=True) as ws:  # verbose=True for debug
            await ws.subscribe(tickers)
            print(f"✅ Subscribed successfully to {tickers}")

            def message_handler(msg: dict):
                try:
                    sym = msg.get("id") or msg.get("symbol") or list(previous_closes.keys())[0]
                    payload = {
                        "symbol": sym,
                        "timestamp": datetime.utcnow().isoformat() + "Z",
                        "lastPrice": round(msg.get("price") or 0, 2),
                        "previousClose": previous_closes.get(sym, 0),
                        "changePercent": round(msg.get("change_percent") or 0, 2),
                        "volume": msg.get("volume") or msg.get("day_volume") or 0
                    }
                    asyncio.create_task(websocket.send_json(payload))
                except Exception as e:
                    print("Handler error:", e)

            await ws.listen(message_handler)

    except WebSocketDisconnect:
        print(f"Client disconnected (multi): {tickers}")
    except Exception as e:
        print("Multi WS error:", e)
        try:
            await websocket.send_json({"error": str(e)})
        except:
            pass


# ==================== SINGLE TICKER WEBSOCKETS (AFTER multi) ====================

@app.websocket("/ws/{ticker}")
async def websocket_indian(websocket: WebSocket, ticker: str):
    await websocket.accept()
    ticker = normalize_indian(ticker)
    # (same code as before - unchanged for simplicity)
    try:
        previous_close = round(yf.Ticker(ticker).fast_info.get("previousClose") or 0, 2)
        async with yf.AsyncWebSocket(verbose=True) as ws:
            await ws.subscribe(ticker)

            def handler(msg):
                payload = {...}  # same as before
                asyncio.create_task(websocket.send_json(payload))

            await ws.listen(handler)
    except Exception as e:
        print("Indian WS error:", e)


@app.websocket("/ws/foreign/{ticker}")
async def websocket_foreign(websocket: WebSocket, ticker: str):
    await websocket.accept()
    ticker = normalize_foreign(ticker)
    # (same code as before)
    try:
        previous_close = round(yf.Ticker(ticker).fast_info.get("previousClose") or 0, 2)
        async with yf.AsyncWebSocket(verbose=True) as ws:
            await ws.subscribe(ticker)

            def handler(msg):
                payload = {...}  # same
                asyncio.create_task(websocket.send_json(payload))

            await ws.listen(handler)
    except Exception as e:
        print("Foreign WS error:", e)

# Run: uvicorn main:app --reload