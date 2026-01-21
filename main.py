from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
import requests
import os
import json
from typing import Dict, Optional
from datetime import datetime

app = FastAPI()

# ===============================
# ENV VARIABLES (SET IN RENDER)
# ===============================
ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
VERIFY_TOKEN = os.getenv("META_VERIFY_TOKEN")

GRAPH_URL = f"https://graph.facebook.com/v22.0/{PHONE_NUMBER_ID}/messages"

# ===============================
# USER STATE MANAGEMENT
# ===============================
user_states: Dict[str, Dict] = {}

def get_user_state(phone: str) -> Dict:
    """Get or create user state"""
    if phone not in user_states:
        user_states[phone] = {
            "current_menu": "main",
            "context": {},
            "last_interaction": datetime.now().isoformat()
        }
    return user_states[phone]

def set_user_state(phone: str, menu: str, context: Optional[Dict] = None):
    """Update user state"""
    state = get_user_state(phone)
    state["current_menu"] = menu
    if context:
        state["context"].update(context)
    state["last_interaction"] = datetime.now().isoformat()

# ===============================
# SEND MESSAGE FUNCTIONS
# ===============================
def send_message(to: str, text: str):
    """Send a simple text message"""
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": text},
    }

    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }

    response = requests.post(GRAPH_URL, json=payload, headers=headers)
    print("SEND STATUS:", response.status_code)
    print("SEND RESPONSE:", response.text)

def send_interactive_message(to: str, text: str, buttons: list):
    """Send message with interactive buttons"""
    button_objects = []
    for i, button in enumerate(buttons[:3]):  # Max 3 buttons
        button_objects.append({
            "type": "reply",
            "reply": {
                "id": f"btn_{i}",
                "title": button
            }
        })
    
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {
                "text": text
            },
            "action": {
                "buttons": button_objects
            }
        }
    }

    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }

    response = requests.post(GRAPH_URL, json=payload, headers=headers)
    print("INTERACTIVE SEND STATUS:", response.status_code)
    print("INTERACTIVE SEND RESPONSE:", response.text)


# ===============================
# WEBHOOK VERIFICATION (GET)
# ===============================
@app.get("/webhook")
async def verify_webhook(request: Request):
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        # MUST return plain text (not JSON)
        return PlainTextResponse(content=challenge, status_code=200)

    return PlainTextResponse(content="Forbidden", status_code=403)


# ===============================
# CONVERSATION FLOW HANDLERS
# ===============================
def handle_main_menu(sender: str, text: str):
    """Handle main menu interactions"""
    text_lower = text.lower().strip()
    
    # Welcome message with menu
    welcome_msg = """🏠 *Welcome to RealEstate Bot!*

I can help you with:
• Search Properties
• Schedule Viewings
• Property Details
• Contact Agent
• Help

Please select an option from the menu below 👇"""
    
    buttons = ["🔍 Search Properties", "📅 Schedule Viewing", "ℹ️ More Options"]
    
    if any(keyword in text_lower for keyword in ["hi", "hello", "hey", "start", "menu", "main"]):
        send_interactive_message(sender, welcome_msg, buttons)
        set_user_state(sender, "main")
        return
    
    # Handle menu selections
    if "1" in text or "search" in text_lower or "🔍" in text:
        handle_search_properties(sender)
    elif "2" in text or "schedule" in text_lower or "viewing" in text_lower or "📅" in text:
        handle_schedule_viewing(sender)
    elif "3" in text or "more" in text_lower or "options" in text_lower or "ℹ️" in text:
        handle_more_options(sender)
    elif "info" in text_lower or "detail" in text_lower:
        handle_property_info(sender)
    elif "contact" in text_lower or "agent" in text_lower or "📞" in text:
        handle_contact_agent(sender)
    elif "help" in text_lower or "❓" in text:
        handle_help(sender)
    else:
        send_interactive_message(sender, welcome_msg, buttons)

def handle_search_properties(sender: str):
    """Handle property search flow"""
    state = get_user_state(sender)
    
    if "search_location" not in state["context"]:
        msg = """🔍 *Property Search*

I can help you find the perfect property!

Please tell me:
• Location (area/city)
• Budget range
• Property type (Apartment/Villa/Plot)

For example: "Looking for 2BHK apartment in Downtown, budget 50-70 lakhs"

Or choose from quick options:"""
        buttons = ["📍 Downtown Properties", "🏙️ Suburban Properties", "🔙 Back to Menu"]
        send_interactive_message(sender, msg, buttons)
        set_user_state(sender, "searching", {"step": "location"})
    else:
        # Process search query
        location = state["context"].get("search_location", "Various locations")
        msg = f"""✅ *Search Results for {location}*

I found some great properties for you:

🏠 *Property 1*
📍 Downtown Area
💰 ₹65 Lakhs
🛏️ 2BHK, 1200 sqft
📞 Property ID: PRO-001

🏠 *Property 2*
📍 Suburban Area
💰 ₹58 Lakhs
🛏️ 3BHK, 1500 sqft
📞 Property ID: PRO-002

🏠 *Property 3*
📍 Beachfront
💰 ₹1.2 Crores
🛏️ 4BHK, 2500 sqft
📞 Property ID: PRO-003

Would you like to:
• Get more details about a property
• Schedule a viewing
• Search for different properties"""
        buttons = ["📋 More Details", "📅 Schedule Viewing", "🔙 Main Menu"]
        send_interactive_message(sender, msg, buttons)
        set_user_state(sender, "search_results")

def handle_schedule_viewing(sender: str):
    """Handle viewing appointment scheduling"""
    state = get_user_state(sender)
    
    if "viewing_date" not in state["context"]:
        msg = """📅 *Schedule Property Viewing*

Let's set up a viewing appointment!

Please provide:
• Property ID (if you have one) or property details
• Preferred date & time
• Your contact number (if different)

You can also choose a quick option:"""
        buttons = ["📅 This Week", "📅 Next Week", "🔙 Back"]
        send_interactive_message(sender, msg, buttons)
        set_user_state(sender, "scheduling", {"step": "date"})
    else:
        msg = """✅ *Viewing Scheduled!*

📅 *Appointment Details:*
Date: [Your selected date]
Time: [Selected time]
Property: [Property details]

📍 *Location:*
[Property address]

👤 *Your Agent:*
John Smith
📞 +91 98765 43210

You'll receive a confirmation message shortly.
Would you like to add this to your calendar?"""
        buttons = ["✅ Confirm", "✏️ Reschedule", "🔙 Menu"]
        send_interactive_message(sender, msg, buttons)
        set_user_state(sender, "viewing_confirmed")

def handle_property_info(sender: str):
    """Handle property information requests"""
    msg = """ℹ️ *Property Information*

Please provide:
• Property ID (e.g., PRO-001)
• Or describe the property you're interested in

I can share:
• Full property details
• Photos & virtual tour
• Location map
• Pricing & financing options
• Nearby amenities

What property would you like to know about?"""
    buttons = ["🏠 Sample Property", "📋 List All"]
    send_interactive_message(sender, msg, buttons)
    set_user_state(sender, "property_info", {"step": "id_request"})

def handle_contact_agent(sender: str):
    """Handle agent contact requests"""
    msg = """📞 *Contact Our Agent*

Our experienced real estate agents are here to help!

👤 *Primary Agent:*
John Smith
📞 +91 98765 43210
✉️ john.smith@realestate.com

👤 *Senior Agent:*
Sarah Johnson
📞 +91 98765 43211
✉️ sarah.j@realestate.com

Would you like to:
• Get immediate callback
• Schedule consultation
• Send inquiry message"""
    buttons = ["📞 Request Callback", "📅 Schedule Call", "🔙 Menu"]
    send_interactive_message(sender, msg, buttons)
    set_user_state(sender, "contact_agent")

def handle_more_options(sender: str):
    """Handle more options submenu"""
    msg = """ℹ️ *More Options*

What would you like to do?

• Property Information
• Contact Agent
• Help & Support"""
    buttons = ["ℹ️ Property Info", "📞 Contact Agent", "❓ Help"]
    send_interactive_message(sender, msg, buttons)
    set_user_state(sender, "more_options")

def handle_help(sender: str):
    """Handle help requests"""
    msg = """❓ *How Can I Help You?*

I'm your real estate assistant! Here's what I can do:

🔍 *Search Properties*
Find properties by location, budget, and type

📅 *Schedule Viewings*
Book appointments to visit properties

ℹ️ *Property Information*
Get detailed info, photos, and pricing

📞 *Contact Agent*
Connect with our expert agents

💡 *Tips:*
• Type "menu" anytime to return to main menu
• Use property IDs (like PRO-001) for quick access
• I can handle multiple requests at once

Need more help? Type your question or select an option:"""
    buttons = ["🔍 How to Search", "📅 How to Book", "🔙 Menu"]
    send_interactive_message(sender, msg, buttons)
    set_user_state(sender, "help")

# ===============================
# WEBHOOK RECEIVER (POST)
# ===============================
@app.post("/webhook")
async def receive_webhook(request: Request):
    body = await request.json()
    print("INCOMING WEBHOOK:")
    print(json.dumps(body, indent=2))

    try:
        entry = body["entry"][0]
        change = entry["changes"][0]
        value = change["value"]

        # Ignore status-only webhooks
        if "messages" not in value:
            return {"status": "ignored"}

        message = value["messages"][0]
        sender = message["from"]
        
        # Handle interactive button responses
        if "interactive" in message:
            text = message["interactive"]["button_reply"]["title"]
            print(f"BUTTON CLICKED: {text} FROM: {sender}")
        else:
            text = message["text"]["body"]
            print(f"TEXT MESSAGE: {text} FROM: {sender}")

        # Get user state
        state = get_user_state(sender)
        current_menu = state["current_menu"]

        # Route to appropriate handler based on state
        text_lower = text.lower()
        if current_menu == "main" or current_menu not in ["searching", "search_results", "scheduling", "viewing_confirmed", "property_info", "property_details", "contact_agent", "help", "more_options"]:
            handle_main_menu(sender, text)
        elif current_menu == "searching" or current_menu == "search_results":
            if "back" in text.lower() or "menu" in text.lower():
                handle_main_menu(sender, "menu")
            elif "detail" in text.lower() or "more" in text.lower():
                handle_property_info(sender)
            elif "viewing" in text.lower() or "schedule" in text.lower():
                handle_schedule_viewing(sender)
            elif "new" in text.lower() or "search" in text.lower():
                state["context"] = {}
                handle_search_properties(sender)
            else:
                # Store search query and show results
                state["context"]["search_location"] = text
                handle_search_properties(sender)
        elif current_menu == "scheduling" or current_menu == "viewing_confirmed":
            if "back" in text.lower() or "menu" in text.lower():
                handle_main_menu(sender, "menu")
            elif "reschedule" in text.lower() or "change" in text.lower():
                state["context"] = {}
                handle_schedule_viewing(sender)
            elif "confirm" in text.lower() or "yes" in text.lower():
                send_message(sender, "✅ Great! Your viewing has been confirmed. We'll send you a reminder 24 hours before your appointment. Thank you!")
                handle_main_menu(sender, "menu")
            else:
                state["context"]["viewing_date"] = text
                handle_schedule_viewing(sender)
        elif current_menu == "property_info":
            if "back" in text.lower() or "menu" in text.lower():
                handle_main_menu(sender, "menu")
            else:
                msg = """🏠 *Property Details - PRO-001*

📍 *Location:* Downtown Area, Main Street
💰 *Price:* ₹65 Lakhs
📏 *Size:* 1200 sqft
🛏️ *Bedrooms:* 2
🚿 *Bathrooms:* 2
🚗 *Parking:* 1 Covered

✨ *Features:*
• Fully furnished
• Modern kitchen
• Balcony with city view
• 24/7 security
• Swimming pool
• Gym access

📍 *Nearby:*
• School: 500m
• Hospital: 1.2km
• Mall: 800m

📸 Photos & virtual tour available
💳 Flexible payment plans

What would you like to do next?"""
                buttons = ["📅 Schedule Viewing", "📞 Contact Agent", "🔙 Menu"]
                send_interactive_message(sender, msg, buttons)
                set_user_state(sender, "property_details")
        elif current_menu == "contact_agent":
            if "back" in text.lower() or "menu" in text.lower():
                handle_main_menu(sender, "menu")
            elif "callback" in text.lower() or "call" in text.lower():
                send_message(sender, "✅ Callback requested! Our agent will call you within 15 minutes. Keep your phone ready!")
                handle_main_menu(sender, "menu")
            elif "schedule" in text.lower():
                handle_schedule_viewing(sender)
            else:
                send_message(sender, "✅ Your message has been forwarded to our agent. They will respond shortly!")
                handle_main_menu(sender, "menu")
        elif current_menu == "more_options":
            if "back" in text.lower() or "menu" in text.lower():
                handle_main_menu(sender, "menu")
            elif "info" in text.lower() or "property" in text_lower or "ℹ️" in text:
                handle_property_info(sender)
            elif "contact" in text.lower() or "agent" in text_lower or "📞" in text:
                handle_contact_agent(sender)
            elif "help" in text.lower() or "❓" in text:
                handle_help(sender)
            else:
                handle_main_menu(sender, text)
        elif current_menu == "help":
            if "back" in text.lower() or "menu" in text.lower():
                handle_main_menu(sender, "menu")
            else:
                handle_main_menu(sender, text)
        elif current_menu == "property_details":
            if "back" in text.lower() or "menu" in text.lower():
                handle_main_menu(sender, "menu")
            elif "viewing" in text.lower() or "schedule" in text_lower or "📅" in text:
                handle_schedule_viewing(sender)
            elif "contact" in text.lower() or "agent" in text_lower or "📞" in text:
                handle_contact_agent(sender)
            else:
                handle_main_menu(sender, text)
        else:
            handle_main_menu(sender, text)

    except Exception as e:
        print("ERROR PROCESSING WEBHOOK:", e)
        import traceback
        traceback.print_exc()

    return {"status": "ok"}
