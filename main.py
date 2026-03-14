
@app.websocket("/ws/sim/{ticker}")
async def websocket_sim_single(websocket: WebSocket, ticker: str):
    await websocket.accept()
    ticker = normalize_indian(ticker)
    print(f"🧪 SIMULATION STARTED: {ticker}")

    try:
        # Start from real last price
        fi = yf.Ticker(ticker).fast_info
        current_price = round(fi.get("lastPrice") or fi.get("previousClose") or 1000, 2)
        prev_close = round(fi.get("previousClose") or current_price, 2)
        volume = random.randint(800000, 5000000)

        while True:
            # Random walk simulation
            change = random.uniform(-4.0, 4.0)
            if random.random() < 0.12:          # occasional bigger swing
                change = random.uniform(-18.0, 18.0)
            
            current_price = max(5.0, round(current_price + change, 2))
            change_percent = round(((current_price - prev_close) / prev_close) * 100, 2)
            volume = int(volume * random.uniform(0.93, 1.07))

            payload = {
                "symbol": ticker,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "lastPrice": current_price,
                "previousClose": prev_close,
                "changePercent": change_percent,
                "volume": volume,
                "mode": "SIMULATION"
            }
            await websocket.send_json(payload)
            await asyncio.sleep(1.1)               # feels very live
    except WebSocketDisconnect:
        print(f"Simulation disconnected: {ticker}")
    except Exception as e:
        print("Sim error:", e)

@app.websocket("/ws/sim/multi")
async def websocket_sim_multi(
    websocket: WebSocket,
    symbols: str = Query(..., description="Comma separated: RELIANCE,TCS,HDFCBANK")
):
    await websocket.accept()
    tickers = [normalize_indian(s.strip()) for s in symbols.split(",") if s.strip()]
    print(f"🧪 MULTI SIMULATION STARTED: {tickers}")

    # Initialize each stock
    prices = {}
    prev_closes = {}
    volumes = {}
    for t in tickers:
        fi = yf.Ticker(t).fast_info
        prices[t] = round(fi.get("lastPrice") or fi.get("previousClose") or 1000, 2)
        prev_closes[t] = round(fi.get("previousClose") or prices[t], 2)
        volumes[t] = random.randint(800000, 5000000)

    try:
        while True:
            for t in tickers:
                change = random.uniform(-4.0, 4.0)
                if random.random() < 0.1:
                    change = random.uniform(-18.0, 18.0)
                
                prices[t] = max(5.0, round(prices[t] + change, 2))
                chg_pct = round(((prices[t] - prev_closes[t]) / prev_closes[t]) * 100, 2)
                volumes[t] = int(volumes[t] * random.uniform(0.93, 1.07))

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
            await asyncio.sleep(1.3)
    except WebSocketDisconnect:
        print("Multi simulation disconnected")
    except Exception as e:
        print("Multi sim error:", e)