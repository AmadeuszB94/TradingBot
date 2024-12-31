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

@app.post("/webhook")
async def webhook(request: Request):
    """Endpoint odbierający webhooki z TradingView."""
    try:
        # Próba odczytania JSON z żądania
        try:
            data = await request.json()
            logger.info(f"Received data: {data}")
        except json.JSONDecodeError:
            logger.error("Invalid JSON payload received")
            return {"error": "Invalid JSON payload"}

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

        # (Dodaj tutaj logikę autoryzacji i przesyłania zleceń do Capital.com)

        return {"message": "Webhook processed successfully"}

    except Exception as e:
        logger.error(f"Error handling webhook: {e}")
        return {"error": "Internal server error"}

@app.get("/")
async def root():
    """Endpoint testowy."""
    return {"message": "Server is running"}
