from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from database import init_db, get_customer, save_reading, get_history, calculate_bill
from keep_alive import start_keep_alive

app = Flask(__name__)

# Initialize database
init_db()

# Start keep alive
start_keep_alive()

# Session storage (in-memory)
sessions = {}

TARIFF = 500  # TZS per cubic meter

def get_session(phone):
    if phone not in sessions:
        sessions[phone] = {"step": "menu"}
    return sessions[phone]

def reset_session(phone):
    sessions[phone] = {"step": "menu"}

def main_menu(lang):
    if lang == "sw":
        return (
            "🚰 *Karibu kwenye Huduma ya Maji*\n\n"
            "Chagua huduma:\n"
            "1️⃣ Soma Mita (Enter Reading)\n"
            "2️⃣ Hesabu Bill\n"
            "3️⃣ Historia ya Malipo\n"
            "4️⃣ Badilisha Lugha (English)\n\n"
            "Jibu namba 1-4"
        )
    else:
        return (
            "🚰 *Welcome to Water Services*\n\n"
            "Choose a service:\n"
            "1️⃣ Submit Meter Reading\n"
            "2️⃣ Calculate Bill\n"
            "3️⃣ Payment History\n"
            "4️⃣ Change Language (Kiswahili)\n\n"
            "Reply with number 1-4"
        )

def handle_message(phone, message):
    session = get_session(phone)
    lang = session.get("lang", "sw")
    step = session.get("step", "menu")
    msg = message.strip()

    # Language toggle
    if msg == "4":
        session["lang"] = "en" if lang == "sw" else "sw"
        lang = session["lang"]
        reset_session(phone)
        sessions[phone]["lang"] = lang
        return main_menu(lang)

    # Main menu
    if step == "menu":
        if msg == "1":
            session["step"] = "ask_account_reading"
            if lang == "sw":
                return "📋 Tafadhali ingiza *namba ya akaunti* yako:"
            else:
                return "📋 Please enter your *account number*:"

        elif msg == "2":
            session["step"] = "ask_account_bill"
            if lang == "sw":
                return "📋 Tafadhali ingiza *namba ya akaunti* yako:"
            else:
                return "📋 Please enter your *account number*:"

        elif msg == "3":
            session["step"] = "ask_account_history"
            if lang == "sw":
                return "📋 Tafadhali ingiza *namba ya akaunti* yako:"
            else:
                return "📋 Please enter your *account number*:"

        else:
            return main_menu(lang)

    # === FLOW: SOMA MITA ===
    elif step == "ask_account_reading":
        customer = get_customer(msg)
        if not customer:
            if lang == "sw":
                return "❌ Akaunti haipatikani. Jaribu tena au andika *menu* kurudi."
            else:
                return "❌ Account not found. Try again or type *menu* to go back."
        session["account"] = msg
        session["customer_name"] = customer["name"]
        session["step"] = "enter_reading"
        if lang == "sw":
            return f"👤 Karibu *{customer['name']}*!\n\nTafadhali ingiza *usomaji wa mita* (m³) wa sasa:"
        else:
            return f"👤 Welcome *{customer['name']}*!\n\nPlease enter current *meter reading* (m³):"

    elif step == "enter_reading":
        if not msg.isdigit():
            if lang == "sw":
                return "❌ Tafadhali ingiza namba sahihi ya usomaji wa mita."
            else:
                return "❌ Please enter a valid meter reading number."
        reading = int(msg)
        account = session["account"]
        save_reading(account, reading)
        reset_session(phone)
        sessions[phone]["lang"] = lang
        if lang == "sw":
            return (
                f"✅ Usomaji wa mita *{reading} m³* umehifadhiwa!\n\n"
                f"Asante. Andika *menu* kuendelea."
            )
        else:
            return (
                f"✅ Meter reading *{reading} m³* saved successfully!\n\n"
                f"Thank you. Type *menu* to continue."
            )

    # === FLOW: HESABU BILL ===
    elif step == "ask_account_bill":
        customer = get_customer(msg)
        if not customer:
            if lang == "sw":
                return "❌ Akaunti haipatikani. Jaribu tena au andika *menu* kurudi."
            else:
                return "❌ Account not found. Try again or type *menu* to go back."
        account = msg
        bill_info = calculate_bill(account)
        reset_session(phone)
        sessions[phone]["lang"] = lang

        if not bill_info:
            if lang == "sw":
                return "⚠️ Hakuna usomaji wa mita uliohifadhiwa. Tafadhali soma mita kwanza."
            else:
                return "⚠️ No meter readings found. Please submit a reading first."

        if lang == "sw":
            return (
                f"💧 *Hesabu ya Bill*\n\n"
                f"👤 Jina: {customer['name']}\n"
                f"📊 Usomaji wa Awali: {bill_info['prev']} m³\n"
                f"📊 Usomaji wa Sasa: {bill_info['curr']} m³\n"
                f"📐 Matumizi: {bill_info['units']} m³\n"
                f"💰 Bei: TZS {TARIFF:,}/m³\n"
                f"🧾 *Jumla: TZS {bill_info['total']:,}*\n\n"
                f"Andika *menu* kuendelea."
            )
        else:
            return (
                f"💧 *Bill Calculation*\n\n"
                f"👤 Name: {customer['name']}\n"
                f"📊 Previous Reading: {bill_info['prev']} m³\n"
                f"📊 Current Reading: {bill_info['curr']} m³\n"
                f"📐 Units Used: {bill_info['units']} m³\n"
                f"💰 Rate: TZS {TARIFF:,}/m³\n"
                f"🧾 *Total: TZS {bill_info['total']:,}*\n\n"
                f"Type *menu* to continue."
            )

    # === FLOW: HISTORIA ===
    elif step == "ask_account_history":
        customer = get_customer(msg)
        if not customer:
            if lang == "sw":
                return "❌ Akaunti haipatikani. Jaribu tena au andika *menu* kurudi."
            else:
                return "❌ Account not found. Try again or type *menu* to go back."
        account = msg
        history = get_history(account)
        reset_session(phone)
        sessions[phone]["lang"] = lang

        if not history:
            if lang == "sw":
                return "📭 Hakuna historia ya usomaji kwa akaunti hii."
            else:
                return "📭 No reading history found for this account."

        lines = []
        if lang == "sw":
            lines.append(f"📜 *Historia ya Usomaji - {customer['name']}*\n")
        else:
            lines.append(f"📜 *Reading History - {customer['name']}*\n")

        for i, record in enumerate(history[-5:], 1):  # Last 5 records
            lines.append(f"{i}. 📅 {record['date']} → {record['reading']} m³")

        lines.append("\nAndika *menu* kuendelea." if lang == "sw" else "\nType *menu* to continue.")
        return "\n".join(lines)

    # Fallback
    else:
        reset_session(phone)
        sessions[phone]["lang"] = lang
        return main_menu(lang)


@app.route("/webhook", methods=["POST"])
def webhook():
    incoming_msg = request.form.get("Body", "").strip()
    from_number = request.form.get("From", "")

    # Handle 'menu' keyword anytime
    if incoming_msg.lower() == "menu":
        reset_session(from_number)
        lang = sessions.get(from_number, {}).get("lang", "sw")
        sessions[from_number] = {"step": "menu", "lang": lang}
        reply = main_menu(lang)
    else:
        reply = handle_message(from_number, incoming_msg)

    resp = MessagingResponse()
    resp.message(reply)
    return str(resp)


@app.route("/")
def home():
    return "🚰 Water Meter Bot is Running!"


if __name__ == "__main__":
    app.run(debug=True)
