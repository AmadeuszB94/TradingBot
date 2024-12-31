import os
import httpx
import asyncio
import logging
from fastapi import FastAPI, Request

# ==========================
# Ustawienia logowania
# ==========================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==========================
# Konfiguracja aplikacji
# ==========================
app = FastAPI()

CAPITAL_API_URL = os.getenv("CAPITAL_API_URL", "https://demo-api-capital.backend-capital.com/api/v1")
CAPITAL_EMAIL = os.getenv("CAPITAL_EMAIL")
CAPITAL_PASSWORD = os.getenv("CAPITAL_PASSWORD")
CAPITAL_API_KEY = os.getenv("CAPITAL_API_KEY")
PING_URL = os.getenv("PING_URL", "https://example-ping-url.onrender.com")

# ==========================
# Pingowanie dla utrzymania serwera
# ==========================
async def keep_alive():
    """Funkcja utrzymująca serwer aktywny przez wysyłanie pingu."""
    while True:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(PING_URL)
                if response.status_code == 200:
                    logger.info("Ping successful: Server is alive")
                else:
                    logger.warning(f"Ping returned status {response.status_code}")
        except Exception as e:
            logger.error(f"Error during ping: {e}")
        await asyncio.sleep(45)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(keep_alive())

# ==========================
# Sprawdzanie zmiennych środowiskowych
# ==========================
@app.on_event("startup")
async def check_environment_variables():
    """Sprawdzanie zmiennych środowiskowych na starcie aplikacji."""
    logger.info("Sprawdzanie zmiennych środowiskowych...")
    logger.info(f"CAPITAL_API_URL: {CAPITAL_API_URL}")
    logger.info(f"CAPITAL_EMAIL: {CAPITAL_EMAIL}")
    logger.info(f"CAPITAL_PASSWORD: {'*' * len(CAPITAL_PASSWORD) if CAPITAL_PASSWORD else 'NOT SET'}")
    logger.info(f"CAPITAL_API_KEY: {'*' * len(CAPITAL_API_KEY) if CAPITAL_API_KEY else 'NOT SET'}")
    if not all([CAPITAL_API_URL, CAPITAL_EMAIL, CAPITAL_PASSWORD, CAPITAL_API_KEY]):
        logger.error("Brakuje jednej lub więcej zmiennych środowiskowych!")

# ==========================
# Autoryzacja w Capital.com
# ==========================
async def authenticate():
    """Autoryzacja w API Capital.com."""
    url = f"{CAPITAL_API_URL}/session"
    payload = {"identifier": CAPITAL_EMAIL, "password": CAPITAL_PASSWORD}
    headers = {"Content-Type": "application/json", "X-CAP-API-KEY": CAPITAL_API_KEY}

    logger.info(f"Attempting authentication with URL: {url}")
    logger.info(f"Payload: {payload}")
    logger.info(f"Headers: {headers}")

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(url, json=payload, headers=headers)
        logger.info(f"Authentication response status: {response.status_code}")
        logger.info(f"Authentication response text: {response.text}")
        if response.status_code == 200:
            logger.info("Authentication successful")
            cst = response.headers.get("CST")
            x_security_token = response.headers.get("X-SECURITY-TOKEN")
            return {"CST": cst, "X-SECURITY-TOKEN": x_security_token}
        else:
            logger.error(f"Authentication failed with error {response.status_code}.")
            logger.error(f"Error details: {response.json()}")
            logger.error("Possible causes of the error:")
            logger.error("1. Check if your API_KEY is correct.")
            logger.error("2. Verify if your EMAIL and PASSWORD are correct.")
            logger.error("3. Ensure your API_KEY is active and linked to the correct account.")
            return None

# ==========================
# Webhook do obsługi zleceń
# ==========================
@app.post("/webhook")
async def webhook(request: Request):
    """Endpoint webhook do obsługi TradingView."""
    try:
        data = await request.json()
        logger.info(f"Received data: {data}")
    except Exception as e:
        logger.error(f"Error parsing JSON: {e}")
        return {"error": "Invalid JSON payload"}

    action = data.get("action", "").upper()
    symbol = data.get("symbol")
    size = data.get("size")
    tp = data.get("tp")
    sl = data.get("sl")

    if not all([action, symbol, size]):
        logger.error("Missing required fields in the request")
        return {"error": "Missing required fields (action, symbol, size)"}

    # Autoryzacja
    tokens = await authenticate()
    if not tokens:
        return {"error": "Authentication failed"}

    # Przygotowanie payload do zlecenia
    payload = {
        "epic": symbol,
        "size": float(size),
        "direction": action,
        "orderType": "MARKET",
        "currencyCode": "USD",
        "limitLevel": float(tp) if tp else None,
        "stopLevel": float(sl) if sl else None,
    }

    headers = {
        "Content-Type": "application/json",
        "CST": tokens["CST"],
        "X-SECURITY-TOKEN": tokens["X-SECURITY-TOKEN"]
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            order_url = f"{CAPITAL_API_URL}/positions"
            response = await client.post(order_url, json=payload, headers=headers)
            if response.status_code == 200:
                logger.info("Order executed successfully")
                return {"message": "Order executed successfully", "details": response.json()}
            else:
                logger.error(f"Order failed: {response.status_code} - {response.text}")
                return {"error": "Order execution failed", "details": response.text}
        except Exception as e:
            logger.error(f"Error sending order: {e}")
            return {"error": "Error sending order"}

# ==========================
# Endpoint testowy (ping)
# ==========================
@app.get("/")
async def root():
    """Testowy endpoint do sprawdzenia stanu serwera."""
    return {"message": "Server is running"}

@app.head("/")
async def root_head():
    """Obsługa metody HEAD dla endpointu głównego (/)."""
    return {"message": "Server is running"}
