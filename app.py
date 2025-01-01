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
CAPITAL_API_URL = "https://demo-api-capital.backend-capital.com/api/v1"
CAPITAL_EMAIL = "am.zg@icloud.com"
CAPITAL_PASSWORD_WITH_ACCENT = "1DawaćSiano2#!"  # Hasło z polskimi znakami
CAPITAL_PASSWORD_NO_ACCENT = "1DawacSiano2#!"    # Hasło bez polskich znaków
CAPITAL_API_KEY = "YIsbQNUrgUV7dY0a"

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
                logger.info("Tokens with Polish characters:")
                logger.info(f"CST: {cst}, X-SECURITY-TOKEN: {x_security_token}")
                return {"CST": cst, "X-SECURITY-TOKEN": x_security_token}
            else:
                logger.error(f"Authentication with Polish characters failed: {response.status_code} - {response.text}")
        except Exception as e:
            logger.error(f"Error during authentication with Polish characters: {e}")

    # Druga próba: Hasło bez polskich znaków
    payload_without_accent = {"identifier": CAPITAL_EMAIL, "password": CAPITAL_PASSWORD_NO_ACCENT}
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.post(url, json=payload_without_accent, headers=headers)
            if response.status_code == 200:
                logger.info("Authentication without Polish characters successful")
                cst = response.headers.get("CST")
                x_security_token = response.headers.get("X-SECURITY-TOKEN")
                logger.info("Tokens without Polish characters:")
                logger.info(f"CST: {cst}, X-SECURITY-TOKEN: {x_security_token}")
                return {"CST": cst, "X-SECURITY-TOKEN": x_security_token}
            else:
                logger.error(f"Authentication without Polish characters failed: {response.status_code} - {response.text}")
        except Exception as e:
            logger.error(f"Error during authentication without Polish characters: {e}")

    return None  # Zwrócenie None, jeśli obie próby się nie powiodły

# Testowanie
async def test_authentication():
    tokens = await authenticate()
    if tokens:
        logger.info("Authentication successful, tokens obtained.")
    else:
        logger.error("Both authentication attempts failed.")

# Wywołanie funkcji testowej (zakładając, że używasz asyncio w kontekście asynchronicznym)
# asyncio.run(test_authentication())
