from flask import Flask, request, jsonify
from database import init_db, get_customer, save_reading, get_history, calculate_bill
from keep_alive import start_keep_alive
import requests
import os

app = Flask(__name__)
init_db()
start_keep_alive()

ACCESS_TOKEN = os.environ.get("META_ACCESS_TOKEN", "EAAYtwx1UHQoBRgVjyuth8kiFsPlamtY6TWuZCe0o15LZBZABJ7a71XsiceDhtDx2cqNioiPvZAQyRZANBoLQLTXDFdVZAwAZBA4q1uq7xHx3dpWZBTzI7SfvBYvZCvjF17sha0OpqsKu88vELhQnn2zyzOg0c1qiLWybHdGkO4I6llyrLZAs6boA0iSoA3JDS1BFgiC9hZCGLLhtu8jVdqWTFkUJebaPhfWyBoA6wZDZD")
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID", "118890686428648")
VERIFY_TOKEN = "water_meter_bot_2024"
TARIFF = 500

sessions = {}

def send_message(to, message):
    url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"}
    data = {"messaging_product": "whatsapp", "to": to, "type": "text", "text": {"body": message}}
    requests.post(url, headers=headers, json=data)

def get_session(phone):
    if phone not in sessions:
        sessions[phone] = {"step": "menu", "lang": "sw"}
    return sessions[phone]

def reset_session(phone):
    lang = sessions.get(phone, {}).get("lang", "sw")
    sessions[phone] = {"step": "menu", "lang": lang}

def main_menu(lang):
    if lang == "sw":
        return "🚰 *Karibu kwenye Huduma ya Maji*\n\nChagua huduma:\n1️⃣ Soma Mita\n2️⃣ Hesabu Bill\n3️⃣ Historia ya Malipo\n4️⃣ Badilisha Lugha (English)\n\nJibu namba 1-4"
    return "🚰 *Welcome to Water Services*\n\nChoose:\n1️⃣ Submit Meter Reading\n2️⃣ Calculate Bill\n3️⃣ Payment History\n4️⃣ Change Language (Kiswahili)\n\nReply 1-4"

def handle_message(phone, message):
    session = get_session(phone)
    lang = session.get("lang", "sw")
    step = session.get("step", "menu")
    msg = message.strip()

    if msg.lower() == "menu":
        reset_session(phone)
        sessions[phone]["lang"] = lang
        return main_menu(lang)

    if step == "menu":
        if msg == "1":
            session["step"] = "ask_account_reading"
            return "📋 Ingiza namba ya akaunti:" if lang == "sw" else "📋 Enter account number:"
        elif msg == "2":
            session["step"] = "ask_account_bill"
            return "📋 Ingiza namba ya akaunti:" if lang == "sw" else "📋 Enter account number:"
        elif msg == "3":
            session["step"] = "ask_account_history"
            return "📋 Ingiza namba ya akaunti:" if lang == "sw" else "📋 Enter account number:"
        elif msg == "4":
            session["lang"] = "en" if lang == "sw" else "sw"
            lang = session["lang"]
            reset_session(phone)
            sessions[phone]["lang"] = lang
            return main_menu(lang)
        else:
            return main_menu(lang)

    elif step == "ask_account_reading":
        customer = get_customer(msg)
        if not customer:
            return "❌ Akaunti haipatikani." if lang == "sw" else "❌ Account not found."
        session["account"] = msg
        session["step"] = "enter_reading"
        return f"👤 Karibu *{customer['name']}*!\n\nIngiza usomaji wa mita (m³):" if lang == "sw" else f"👤 Welcome *{customer['name']}*!\n\nEnter meter reading (m³):"

    elif step == "enter_reading":
        if not msg.isdigit():
            return "❌ Ingiza namba sahihi." if lang == "sw" else "❌ Enter a valid number."
        save_reading(session["account"], int(msg))
        reset_session(phone)
        sessions[phone]["lang"] = lang
        return f"✅ Usomaji *{msg} m³* umehifadhiwa!\n\nAndika *menu* kuendelea." if lang == "sw" else f"✅ Reading *{msg} m³* saved!\n\nType *menu* to continue."

    elif step == "ask_account_bill":
        customer = get_customer(msg)
        if not customer:
            return "❌ Akaunti haipatikani." if lang == "sw" else "❌ Account not found."
        bill = calculate_bill(msg)
        reset_session(phone)
        sessions[phone]["lang"] = lang
        if not bill:
            return "⚠️ Soma mita kwanza." if lang == "sw" else "⚠️ Submit a reading first."
        if lang == "sw":
            return f"💧 *Hesabu ya Bill*\n\n👤 {customer['name']}\n📊 Awali: {bill['prev']} m³\n📊 Sasa: {bill['curr']} m³\n📐 Matumizi: {bill['units']} m³\n💰 Bei: TZS {TARIFF:,}/m³\n🧾 *Jumla: TZS {bill['total']:,}*\n\nAndika *menu* kuendelea."
        return f"💧 *Bill*\n\n👤 {customer['name']}\n📊 Prev: {bill['prev']} m³\n📊 Curr: {bill['curr']} m³\n📐 Units: {bill['units']} m³\n💰 TZS {TARIFF:,}/m³\n🧾 *Total: TZS {bill['total']:,}*\n\nType *menu* to continue."

    elif step == "ask_account_history":
        customer = get_customer(msg)
        if not customer:
            return "❌ Akaunti haipatikani." if lang == "sw" else "❌ Account not found."
        history = get_history(msg)
        reset_session(phone)
        sessions[phone]["lang"] = lang
        if not history:
            return "📭 Hakuna historia." if lang == "sw" else "📭 No history found."
        lines = [f"📜 *Historia - {customer['name']}*\n"]
        for i, r in enumerate(history[:5], 1):
            lines.append(f"{i}. 📅 {r['date']} → {r['reading']} m³")
        lines.append("\nAndika *menu* kuendelea." if lang == "sw" else "\nType *menu* to continue.")
        return "\n".join(lines)

    reset_session(phone)
    sessions[phone]["lang"] = lang
    return main_menu(lang)

@app.route("/webhook", methods=["GET"])
def verify():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge, 200
    return "Forbidden", 403

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    try:
        messages = data["entry"][0]["changes"][0]["value"].get("messages", [])
        if messages:
            phone = messages[0]["from"]
            text = messages[0]["text"]["body"]
            reply = handle_message(phone, text)
            send_message(phone, reply)
    except Exception as e:
        print(f"Error: {e}")
    return jsonify({"status": "ok"}), 200

@app.route("/")
def home():
    return "🚰 Water Meter Bot (Meta API) is Running!"

if __name__ == "__main__":
    app.run(debug=True)
