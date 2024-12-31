from fastapi import FastAPI, Request
import httpx
import os
import asyncio
import json
import logging

# Inicjalizacja aplikacji i logów
app = FastAPI()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Zmienne środowiskowe
CAPITAL_API_URL = "https://demo-api-capital.backend-capital.com/api/v1"
CAPITAL_EMAIL = os.getenv("CAPITAL_EMAIL")
CAPITAL_PASSWORD = os.getenv("CAPITAL_PASSWORD")
CAPITAL_API_KEY = os.getenv("CAPITAL_API_KEY")
PING_URL = os.getenv("PING_URL")

# Cache tokenów sesji
SESSION_CACHE = {"CST": None, "X-SECURITY-TOKEN": None, "expires_at": 0}


@app.on_event("startup")
async def startup_event():
    """Uruchomienie pingu przy starcie aplikacji."""
    asyncio.create_task(keep_alive())


async def keep_alive():
    """Funkcja pingująca serwer co 45 sekund, aby utrzymać go aktywnym."""
    while True:
        try:
            if PING_URL:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.get(PING_URL)
                    if response.status_code == 200:
                        logger.info("Ping successful: Server is alive")
                    else:
                        logger.warning(f"Ping failed with status code: {response.status_code}")
        except Exception as e:
            logger.error(f"Ping error: {e}")
        await asyncio.sleep(45)


async def authenticate():
    """Autoryzacja w Capital.com."""
    global SESSION_CACHE

    # Jeśli tokeny są nadal ważne, użyj ich
    if SESSION_CACHE["expires_at"] > asyncio.get_event_loop().time():
        logger.info("Using cached session tokens")
        return SESSION_CACHE

    async with httpx.AsyncClient(timeout=10.0) as client:
        payload = {"identifier": CAPITAL_EMAIL, "password": CAPITAL_PASSWORD}
        headers = {"Content-Type": "application/json", "X-CAP-API-KEY": CAPITAL_API_KEY}
        try:
            response = await client.post(f"{CAPITAL_API_URL}/session", json=payload, headers=headers)
            if response.status_code == 200:
                logger.info("Authentication successful")
                SESSION_CACHE["CST"] = response.headers.get("CST")
                SESSION_CACHE["X-SECURITY-TOKEN"] = response.headers.get("X-SECURITY-TOKEN")
                SESSION_CACHE["expires_at"] = asyncio.get_event_loop().time() + 600  # 10 minut ważności
                return SESSION_CACHE
            else:
                logger.error(f"Authentication failed: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"Error during authentication: {e}")
            return None


async def send_trade(session_tokens, action, symbol, size, tp=None, sl=None):
    """Wysyłanie zlecenia do Capital.com."""
    headers = {
        "Content-Type": "application/json",
        "CST": session_tokens["CST"],
        "X-SECURITY-TOKEN": session_tokens["X-SECURITY-TOKEN"]
    }
    payload = {
        "epic": symbol,
        "size": float(size),
        "direction": action.upper(),
        "orderType": "MARKET",
        "currencyCode": "USD"
    }
    if tp:
        payload["limitLevel"] = float(tp)
    if sl:
        payload["stopLevel"] = float(sl)

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.post(f"{CAPITAL_API_URL}/positions", json=payload, headers=headers)
            if response.status_code == 200:
                logger.info(f"Trade executed successfully: {response.json()}")
                return {"message": "Trade executed successfully", "details": response.json()}
            else:
                logger.error(f"Failed to execute trade: {response.status_code} - {response.text}")
                return {"error": "Failed to execute trade", "details": response.text}
        except Exception as e:
            logger.error(f"Error during trade execution: {e}")
            return {"error": f"Error during trade execution: {e}"}


@app.post("/webhook")
async def webhook(request: Request):
    """Endpoint odbierający webhooki z TradingView."""
    try:
        # Próba odczytania JSON z żądania
        data = await request.json()
        logger.info(f"Received data: {data}")

        # Walidacja wymaganych danych
        action = data.get("action")
        symbol = data.get("symbol")
        size = data.get("size")
        tp = data.get("tp")
        sl = data.get("sl")

        if not all([action, symbol, size]):
            logger.error("Missing required fields: action, symbol, or size")
            return {"error": "Missing required fields: action, symbol, or size"}

        logger.info(f"Processing order: Action={action}, Symbol={symbol}, Size={size}, TP={tp}, SL={sl}")

        # Autoryzacja w Capital.com
        session_tokens = await authenticate()
        if not session_tokens:
            return {"error": "Authentication failed"}

        # Wysyłanie zlecenia do Capital.com
        trade_response = await send_trade(session_tokens, action, symbol, size, tp, sl)
        return trade_response

    except Exception as e:
        logger.error(f"Error handling webhook: {e}")
        return {"error": "Internal server error"}


@app.get("/")
async def root():
    """Endpoint testowy."""
    return {"message": "Server is running"}
