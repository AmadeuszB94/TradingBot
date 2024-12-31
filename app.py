import os
import httpx
import asyncio
import logging
from fastapi import FastAPI, Request
from python_decouple import config

# ==========================
# Ustawienia logowania
# ==========================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("app")

# ==========================
# Konfiguracja aplikacji
# ==========================
app = FastAPI()

# ==========================
# Zmienne środowiskowe
# ==========================
CAPITAL_API_URL = os.getenv("CAPITAL_API_URL", "https://demo-api-capital.backend-capital.com/api/v1")
CAPITAL_EMAIL = os.getenv("CAPITAL_EMAIL")
CAPITAL_PASSWORD = os.getenv("CAPITAL_PASSWORD")
CAPITAL_API_KEY = os.getenv("CAPITAL_API_KEY")

PING_URL = os.getenv("PING_URL", "https://example-ping-url.onrender.com")

# ==========================
# Funkcja utrzymania serwera
# ==========================
async def keep_alive():
    while True:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(PING_URL)
                if response.status_code == 200:
                    logger.info("Ping successful: Server is alive")
                else:
                    logger.warning(f"Ping failed with status: {response.status_code}")
        except Exception as e:
            logger.error(f"Ping error: {e}")
        await asyncio.sleep(45)

@app.on_event("startup")
async def startup_event():
    # Logowanie zmiennych środowiskowych
    logger.info("Starting application with the following environment variables:")
    logger.info(f"CAPITAL_API_URL: {CAPITAL_API_URL}")
    logger.info(f"CAPITAL_EMAIL: {CAPITAL_EMAIL}")
    logger.info(f"CAPITAL_API_KEY: {CAPITAL_API_KEY}")
    asyncio.create_task(keep_alive())

# ==========================
# Funkcja autoryzacji
# ==========================
async def authenticate():
    url = f"{CAPITAL_API_URL}/session"
    payload = {"identifier": CAPITAL_EMAIL, "password": CAPITAL_PASSWORD}
    headers = {"Content-Type": "application/json", "X-CAP-API-KEY": CAPITAL_API_KEY}

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(url, json=payload, headers=headers)
        if response.status_code == 200:
            session_data = response.json()
            cst = response.headers.get("CST")
            x_security_token = response.headers.get("X-SECURITY-TOKEN")
            logger.info("Authentication successful")
            return {"CST": cst, "X-SECURITY-TOKEN": x_security_token}
        else:
            logger.error(f"Authentication failed: {response.status_code} - {response.text}")
            if "errorCode" in response.json():
                logger.error(f"Error code from API: {response.json().get('errorCode')}")
            return None

# ==========================
# Endpoint webhooka
# ==========================
@app.post("/webhook")
async def webhook(request: Request):
    try:
        data = await request.json()
        logger.info(f"Received data: {data}")
    except Exception as e:
        logger.error(f"Error parsing request data: {e}")
        return {"error": "Invalid JSON data"}

    action = data.get("action")
    symbol = data.get("symbol")
    size = data.get("size")
    tp = data.get("tp")
    sl = data.get("sl")

    if not action or not symbol or not size:
        logger.error("Missing required fields in webhook payload")
        return {"error": "Missing required fields"}

    session_tokens = await authenticate()
    if not session_tokens:
        return {"error": "Authentication failed"}

    logger.info(f"Processing order: Action={action}, Symbol={symbol}, Size={size}, TP={tp}, SL={sl}")
    payload = {
        "epic": symbol,
        "size": float(size),
        "direction": action.upper(),
        "orderType": "MARKET",
        "currencyCode": "USD",
    }
    if tp:
        payload["limitLevel"] = float(tp)
    if sl:
        payload["stopLevel"] = float(sl)

    headers = {
        "Content-Type": "application/json",
        "CST": session_tokens["CST"],
        "X-SECURITY-TOKEN": session_tokens["X-SECURITY-TOKEN"],
    }

    url = f"{CAPITAL_API_URL}/positions"
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(url, json=payload, headers=headers)
        if response.status_code == 200:
            logger.info(f"Order executed successfully: {response.json()}")
            return {"message": "Order executed successfully", "details": response.json()}
        else:
            logger.error(f"Order execution failed: {response.status_code} - {response.text}")
            return {"error": "Order execution failed", "details": response.text}

@app.get("/")
async def root():
    return {"message": "Server is running"}
