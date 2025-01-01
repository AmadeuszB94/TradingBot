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

# Wszystkie dane zapisane w kodzie
CAPITAL_API_URL = "https://demo-api-capital.backend-capital.com/api/v1"
CAPITAL_EMAIL = "am.zg@icloud.com"
CAPITAL_PASSWORD_WITH_ACCENT = "1DawaćSiano2#!"  # Hasło z polskimi znakami
CAPITAL_PASSWORD_NO_ACCENT = "1DawacSiano2#!"    # Hasło bez polskich znaków
CAPITAL_API_KEY = "YIsbQNUrgUV7dY0a"
PING_URL = "https://tradingbot-qi86.onrender.com"

# ==========================
# Pingowanie dla utrzymania serwera Render
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
        await asyncio.sleep(45)  # Ping co 45 sekund

# ==========================
# Pingowanie dla utrzymania aktywności API Capital.com
# ==========================
async def keep_api_alive():
    """Funkcja podtrzymująca aktywność API Capital.com."""
    while True:
        tokens = await authenticate()  # Uwierzytelnienie przed pingowaniem
        if not tokens:
            logger.error("Cannot ping Capital.com API because authentication failed.")
        else:
            url = f"{CAPITAL_API_URL}/ping"
            headers = {
                "CST": tokens["CST"],
                "X-SECURITY-TOKEN": tokens["X-SECURITY-TOKEN"]
            }
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.get(url, headers=headers)
                    if response.status_code == 200:
                        logger.info("API ping successful: Capital.com session is alive")
                    else:
                        logger.warning(f"API ping returned status {response.status_code}")
            except Exception as e:
                logger.error(f"Error during API ping: {e}")
        await asyncio.sleep(540)  # Ping co 9 minut (540 sekund)

# ==========================
# Autoryzacja w Capital.com z obsługą dwóch prób logowania
# ==========================
async def authenticate():
    """Autoryzacja w API Capital.com z dwoma próbami logowania."""
    url = f"{CAPITAL_API_URL}/session"
    
    # Pierwsza próba: Hasło z polskimi znakami
    payload_with_accent = {"identifier": CAPITAL_EMAIL, "password": CAPITAL_PASSWORD_WITH_ACCENT}
    headers = {"Content-Type": "application/json", "X-CAP-API-KEY": CAPITAL_API_KEY}
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.post(url, json=payload_with_accent, headers=headers)
            if response.status_code == 200:
                logger.info("Authentication with Polish characters successful")
                cst = response.headers.get("CST")
                x_security_token = response.headers.get("X-SECURITY-TOKEN")
                return {"CST": cst, "X-SECURITY-TOKEN": x_security_token}
            elif response.status_code == 401:
                logger.error(f"Authentication failed with Polish characters: {response.status_code} - {response.text}")
            else:
                logger.error(f"Unexpected response with Polish characters: {response.status_code} - {response.text}")
        except Exception as e:
            logger.error(f"Error during authentication with Polish characters: {e}")

    # Druga próba: Hasło bez polskich znaków
    payload_no_accent = {"identifier": CAPITAL_EMAIL, "password": CAPITAL_PASSWORD_NO_ACCENT}
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.post(url, json=payload_no_accent, headers=headers)
            if response.status_code == 200:
                logger.info("Authentication without Polish characters successful")
                cst = response.headers.get("CST")
                x_security_token = response.headers.get("X-SECURITY-TOKEN")
                return {"CST": cst, "X-SECURITY-TOKEN": x_security_token}
            elif response.status_code == 401:
                logger.error(f"Authentication failed without Polish characters: {response.status_code} - {response.text}")
            else:
                logger.error(f"Unexpected response without Polish characters: {response.status_code} - {response.text}")
        except Exception as e:
            logger.error(f"Error during authentication without Polish characters: {e}")

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

    # Sprawdzenie wymaganych pól
    if not action or not symbol or not size:
        logger.error("Missing required fields in the request")
        return {"error": "Missing required fields (action, symbol, size)"}

    try:
        size = float(size)  # Sprawdzenie, czy size jest liczbą
        if size <= 0:
            raise ValueError("Size must be a positive number")
    except ValueError as e:
        logger.error(f"Invalid size value: {e}")
        return {"error": "Invalid size value. Must be a positive number."}

    # Autoryzacja
    tokens = await authenticate()
    if not tokens:
        return {"error": "Authentication failed"}

    # Przygotowanie payload do zlecenia
    payload = {
        "epic": symbol,
        "size": size,
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

# ==========================
# Uruchamianie funkcji pingowania
# ==========================
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(keep_alive())       # Pingowanie Render co 45 sekund
    asyncio.create_task(keep_api_alive())  # Pingowanie API Capital.com co 9 minut
