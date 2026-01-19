from fastapi import FastAPI, Request
import requests
import os

app = FastAPI()

# ===============================
# CONFIG (ENV VARIABLES)
# ===============================
GUPSHUP_API_KEY = os.environ.get("GUPSHUP_API_KEY")
SANDBOX_NUMBER = os.environ.get("SANDBOX_NUMBER")
# In-memory state (sandbox demo only)
user_state = {}
user_data = {}

# ===============================
# SEND MESSAGE FUNCTION
# ===============================
def send_message(to, text):
    url = "https://api.gupshup.io/wa/api/v1/msg"

    payload = {
        "channel": "whatsapp",
        "source": SANDBOX_NUMBER,
        "destination": to,
        "message": f'{{"type":"text","text":"{text}"}}'
    }

    headers = {
        "apikey": GUPSHUP_API_KEY,
        "Content-Type": "application/x-www-form-urlencoded"
    }

    requests.post(url, data=payload, headers=headers)

# ===============================
# WEBHOOK ENDPOINT
# ===============================
@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()

    payload = data.get("payload", {})
    user = payload.get("sender")
    text = payload.get("text", "").strip()

    if not user or not text:
        return {"status": "ignored"}

    text_lower = text.lower()

    # INIT USER
    if user not in user_state:
        user_state[user] = "START"
        user_data[user] = {}
        send_message(
            user,
            "👋 Welcome!\nWhat are you looking for?\n\n1️⃣ Buy Property\n2️⃣ Rent Property"
        )
        return {"status": "ok"}

    # ===============================
    # FLOW LOGIC
    # ===============================
    state = user_state[user]

    if state == "START":
        if text_lower == "1":
            user_state[user] = "BUDGET"
            user_data[user]["type"] = "Buy"
            send_message(user, "💰 What is your budget?")
        elif text_lower == "2":
            user_state[user] = "CITY"
            user_data[user]["type"] = "Rent"
            send_message(user, "📍 Which city are you looking in?")
        else:
            send_message(user, "Please reply with 1 or 2")

    elif state == "BUDGET":
        user_data[user]["budget"] = text
        user_state[user] = "CITY"
        send_message(user, "📍 Which city are you looking in?")

    elif state == "CITY":
        user_data[user]["city"] = text
        summary = (
            f"✅ Details received:\n"
            f"Type: {user_data[user].get('type')}\n"
            f"Budget: {user_data[user].get('budget', 'N/A')}\n"
            f"City: {user_data[user].get('city')}\n\n"
            f"Our agent will contact you shortly."
        )
        send_message(user, summary)

        # CLEAR STATE
        user_state.pop(user, None)
        user_data.pop(user, None)

    return {"status": "ok"}
