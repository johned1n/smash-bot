# SMASH BOT – FINAL 24/7 VERSION
# Just change the TOKEN and run!

import telebot
import yfinance as yf
import time
import threading
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# CHANGE THIS LINE ONLY!
TOKEN = "YOUR_BOT_TOKEN_HERE"          # ← PUT YOUR REAL TOKEN HERE

bot = telebot.TeleBot(TOKEN)

# Storage
alerts = {}                    # {user_id: [{"ticker":"AAPL", "price":200, "dir":"above"}]}
waiting_for_price = {}         # {user_id: "AAPL"}  ← user is typing price

# Popular stocks shown when user types /alert
ALERT_STOCKS = [
    "AAPL", "MSFT", "NVDA", "TSLA", "GOOGL", "AMZN", "META", "NFLX",
    "AMD", "AVGO", "ADBE", "ORCL", "CRM", "INTC", "PYPL", "QCOM",
    "BTC-USD", "ETH-USD", "SOL-USD", "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS"
]

# BULLETPROOF PRICE FUNCTION
def get_price(ticker):
    ticker = ticker.upper()
    if ticker.endswith("IN"):
        ticker = ticker.replace("IN", ".NS")
    try:
        data = yf.download(tickers=ticker, period="5d", interval="1m", progress=False, auto_adjust=True, threads=False)
        if not data.empty:
            return round(float(data["Close"].iloc[-1]), 4)
    except:
        pass
    try:
        hist = yf.Ticker(ticker).history(period="1d")
        if not hist.empty:
            return round(hist["Close"].iloc[-1], 4)
    except:
        pass
    return None

# BACKGROUND ALERT CHECKER (runs forever)
def alert_checker():
    print("Alert checker started – watching stocks 24/7")
    while True:
        time.sleep(90)
        for user_id in list(alerts.keys()):
            for alert in alerts[user_id][:]:
                p = get_price(alert["ticker"])
                if p and ((alert["dir"] == "above" and p >= alert["price"]) or
                          (alert["dir"] == "below" and p <= alert["price"])):
                    bot.send_message(user_id,
                        f"SMASH ALERT!!!\n\n"
                        f"{alert['ticker']} just hit *${p:,}*\n"
                        f"Target: {alert['dir']} ${alert['price']}",
                        parse_mode="Markdown")
                    alerts[user_id].remove(alert)

threading.Thread(target=alert_checker, daemon=True).start()

# BUTTONS
def stock_buttons():
    kb = InlineKeyboardMarkup(row_width=4)
    for s in ALERT_STOCKS:
        kb.add(InlineKeyboardButton(s, callback_data="setalert_" + s))
    return kb

# COMMANDS
@bot.message_handler(commands=['start'])
def start(m):
    bot.reply_to(m, """
*SMASH – Ultimate Stock Alert Bot*

• Type: AAPL TSLA NVDA → get clickable prices
• /top50 → Top 50 stocks
• /alert → Set alert with buttons
• /mylist → Your alerts
• /clear → Remove all alerts
    """, parse_mode="Markdown")

@bot.message_handler(commands=['top50'])
def top50(m):
    kb = InlineKeyboardMarkup(row_width=4)
    top = ["AAPL","MSFT","NVDA","TSLA","GOOGL","AMZN","META","LLY","AVGO","JPM",
           "V","JNJ","WMT","MA","PG","HD","DIS","BAC","ADBE","NFLX"]
    for s in top:
        kb.add(InlineKeyboardButton(s, callback_data=s))
    bot.send_message(m.chat.id, "Top 50 – Click any stock", reply_markup=kb)

@bot.message_handler(commands=['alert'])
def alert_start(m):
    bot.send_message(m.chat.id, "*Choose stock to set alert*", reply_markup=stock_buttons(), parse_mode="Markdown")

# User clicked a stock to set alert
@bot.callback_query_handler(func=lambda call: call.data.startswith("setalert_"))
def alert_stock_chosen(call):
    ticker = call.data.replace("setalert_", "")
    waiting_for_price[call.message.chat.id] = ticker
    bot.answer_callback_query(call.id, f"{ticker} selected")
    bot.send_message(call.message.chat.id,
        f"*You selected {ticker}*\n\n"
        "Now send the price:\n"
        "• `200` → alert when *above* $200\n"
        "• `150 below` → alert when *below* $150",
        parse_mode="Markdown")

# User typed the price
@bot.message_handler(func=lambda m: m.chat.id in waiting_for_price)
def price_received(m):
    ticker = waiting_for_price[m.chat.id]
    text = m.text.strip().lower()
    try:
        if "below" in text:
            price = float(text.split("below")[0].strip())
            direction = "below"
        else:
            price = float(text.replace("below","").strip())
            direction = "above"

        alerts.setdefault(m.chat.id, []).append({"ticker":ticker, "price":price, "dir":direction})
        bot.reply_to(m, f"ALERT SET!\n{ticker} {direction} ${price:,}", parse_mode="Markdown")
        del waiting_for_price[m.chat.id]
    except:
        bot.reply_to(m, "Send a number! Example: 180 or 150 below")

# Click any stock → get price
@bot.callback_query_handler(func=lambda call: not call.data.startswith("setalert_"))
def price_click(call):
    ticker = call.data.upper()
    p = get_price(ticker)
    if p:
        bot.answer_callback_query(call.id, f"{ticker} = ${p:,}", show_alert=True)
        bot.send_message(call.message.chat.id, f"*{ticker}*\nLive Price: `${p:,}`", parse_mode="Markdown")

# User types tickers → show buttons
@bot.message_handler(func=lambda m: True)
def text_handler(m):
    tickers = [t.upper() for t in m.text.replace(","," ").split() if 2<=len(t)<=12]
    if tickers and all(t.replace("-","").replace(".","").isalnum() for t in tickers):
        kb = InlineKeyboardMarkup(row_width=4)
        for t in tickers:
            kb.add(InlineKeyboardButton(t, callback_data=t))
        bot.send_message = bot.send_message(m.chat.id, "Click for live price", reply_markup=kb)

@bot.message_handler(commands=['mylist'])
def mylist(m):
    lst = alerts.get(m.chat.id, [])
    if not lst:
        bot.reply_to(m, "No active alerts")
        return
    txt = "*Your Alerts*\n\n"
    for a in lst:
        txt += f"• {a['ticker']} {a['dir']} ${a['price']:,}\n"
    bot.reply_to(m, txt, parse_mode="Markdown")

@bot.message_handler(commands=['clear'])
def clear(m):
    alerts[m.chat.id] = []
    bot.reply_to(m, "All alerts cleared!")

# START THE BOT
print("SMASH BOT IS ONLINE 24/7!")
bot.infinity_polling()
