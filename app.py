from fastapi import FastAPI, Request
import httpx
import os
import asyncio
import json

app = FastAPI()

CAPITAL_API_URL = "https://demo-api-capital.backend-capital.com/api/v1"
CAPITAL_EMAIL = os.getenv("CAPITAL_EMAIL")
CAPITAL_PASSWORD = os.getenv("CAPITAL_PASSWORD")
CAPITAL_API_KEY = os.getenv("CAPITAL_API_KEY")
PING_URL = os.getenv("PING_URL")  # Adres URL aplikacji, np. https://tradingbot-qi86.onrender.com

@app.on_event("startup")
async def startup_event():
    # Uruchomienie zadania pingującego
    asyncio.create_task(keep_alive())

async def keep_alive():
    """Funkcja pingująca serwer co 45 sekund, aby utrzymać go aktywnym."""
    while True:
        try:
            if PING_URL:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.get(PING_URL)
                    if response.status_code == 200:
                        print("Ping successful")
                    else:
                        print(f"Ping failed with status code: {response.status_code}")
        except Exception as e:
            print(f"Ping error: {e}")
        await asyncio.sleep(45)

@app.post("/webhook")
async def webhook(request: Request):
    try:
        # Próba odczytania JSON z żądania
        try:
            data = await request.json()
        except json.JSONDecodeError:
            return {"error": "Invalid JSON payload"}
        
        # Weryfikacja, czy wymagane dane są obecne
        action = data.get("action")
        symbol = data.get("symbol")
        size = data.get("size")
        tp = data.get("tp")
        sl = data.get("sl")
        
        if not all([action, symbol, size]):
            return {"error": "Missing required fields: action, symbol, or size"}

        # Logowanie odebranych danych
        print(f"Received data: {data}")

        # (Dodaj tutaj logikę autoryzacji i przesyłania zleceń do Capital.com)

        return {"message": "Webhook processed successfully"}

    except Exception as e:
        print(f"Error handling webhook: {e}")
        return {"error": "Internal server error"}

@app.get("/")
async def root():
    return {"message": "Server is running"}
