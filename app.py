from fastapi import FastAPI, Request

app = FastAPI()

@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    print("Received data:", data)
    return {"message": "Webhook received", "data": data}

@app.get("/")
async def root():
    return {"message": "Server is running"}
