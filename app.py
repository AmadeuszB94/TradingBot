# ==========================
# Autoryzacja w Capital.com
# ==========================
async def authenticate():
    """Autoryzacja w API Capital.com."""
    url = f"{CAPITAL_API_URL}/session"
    payload = {"identifier": CAPITAL_EMAIL, "password": CAPITAL_PASSWORD}
    headers = {"Content-Type": "application/json", "X-CAP-API-KEY": CAPITAL_API_KEY}

    # Logowanie używanych danych (bez wyświetlania hasła)
    logger.info("Attempting authentication with Capital.com API")
    logger.info(f"API URL: {url}")
    logger.info(f"Email: {CAPITAL_EMAIL}")
    logger.info(f"API Key: {'*' * len(CAPITAL_API_KEY) if CAPITAL_API_KEY else 'NOT SET'}")
    logger.info(f"Password: {'*' * len(CAPITAL_PASSWORD) if CAPITAL_PASSWORD else 'NOT SET'}")

    # Sprawdzenie brakujących zmiennych
    if not CAPITAL_EMAIL or not CAPITAL_PASSWORD or not CAPITAL_API_KEY:
        logger.error("Missing one or more required environment variables for authentication.")
        if not CAPITAL_EMAIL:
            logger.error("CAPITAL_EMAIL is missing or not set.")
        if not CAPITAL_PASSWORD:
            logger.error("CAPITAL_PASSWORD is missing or not set.")
        if not CAPITAL_API_KEY:
            logger.error("CAPITAL_API_KEY is missing or not set.")
        return None

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.post(url, json=payload, headers=headers)
            if response.status_code == 200:
                logger.info("Authentication successful")
                cst = response.headers.get("CST")
                x_security_token = response.headers.get("X-SECURITY-TOKEN")
                return {"CST": cst, "X-SECURITY-TOKEN": x_security_token}
            elif response.status_code == 401:
                logger.error(f"Authentication failed: {response.status_code} - {response.text}")
                logger.error("Possible reasons:")
                logger.error("- Invalid email or password.")
                logger.error("- Invalid or inactive API key.")
                logger.error("- Check if you're using the correct endpoint for demo or live.")
            else:
                logger.error(f"Unexpected response: {response.status_code} - {response.text}")
        except Exception as e:
            logger.error(f"Error during authentication: {e}")
    return None
