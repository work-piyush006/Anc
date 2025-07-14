import logging
import datetime
import asyncio
import yfinance as yf
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
from apscheduler.schedulers.asyncio import AsyncIOScheduler

BOT_TOKEN = '7048022807:AAG2SBiqry73c_d7IjdVxRYOAjeo6awQMzI'
ADMIN_USER_ID = 1234567890  # Replace with your Telegram User ID
TWELVE_DATA_API_KEY = '78f87bf9df324fe8ac3709f034f70110'

logging.basicConfig(level=logging.INFO)
premium_users = set()
last_refresh_date = None
cached_picks = {}
cached_news = []

def fetch_twelve_data(symbol):
    url = f'https://api.twelvedata.com/price?symbol={symbol}&apikey={TWELVE_DATA_API_KEY}'
    response = requests.get(url).json()
    return response.get('price', 'N/A')

def fetch_yfinance_data(symbol):
    stock = yf.Ticker(symbol)
    data = stock.info
    return data.get('currentPrice', 'N/A')

def fetch_intraday_picks():
    stocks = {
        'Top Picks': ['RELIANCE', 'TCS', 'INFY'],
        'Under ₹1000-1500': ['HDFCBANK', 'ICICIBANK'],
        'Under ₹500-1000': ['SBIN', 'AXISBANK'],
        'Under ₹100-500': ['TATAPOWER'],
        'Penny Stocks': ['SUZLON']
    }
    picks = {}
    for category, symbols in stocks.items():
        picks[category] = []
        for sym in symbols:
            price = fetch_twelve_data(sym) or fetch_yfinance_data(sym)
            picks[category].append(f'{sym} - ₹{price}')
    return picks

def fetch_market_news():
    return [
        "Nifty climbs amid positive global cues.",
        "RBI expected to maintain repo rates.",
        "Tech stocks lead today's rally."
    ]

def refresh_data():
    global last_refresh_date, cached_picks, cached_news
    today = datetime.date.today()
    if last_refresh_date != today:
        cached_picks = fetch_intraday_picks()
        cached_news = fetch_market_news()
        last_refresh_date = today
        logging.info("Market data refreshed.")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton('📈 Intraday Picks', callback_data='intraday')],
        [InlineKeyboardButton('📰 Market News', callback_data='news')],
        [InlineKeyboardButton('💳 Buy Premium', callback_data='buy_premium')],
        [InlineKeyboardButton('📋 My User ID', callback_data='my_user_id')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('👋 Welcome to TopIntradayPicks Bot!\n\nPlease choose an option:', reply_markup=reply_markup)

async def handle_intraday(update: Update, context: ContextTypes.DEFAULT_TYPE):
    refresh_data()
    user_id = update.effective_user.id
    msg = "📈 *Intraday Picks*\n\n"
    for category, stocks in cached_picks.items():
        if user_id in premium_users or category != 'Top Picks':
            msg += f'*{category}*:\n' + '\n'.join(stocks) + '\n\n'
        else:
            msg += f'*{category}*:\n(Available in Premium)\n\n'
    await update.callback_query.message.reply_text(msg, parse_mode='Markdown')

async def handle_news(update: Update, context: ContextTypes.DEFAULT_TYPE):
    refresh_data()
    msg = "📰 *Market News*\n\n"
    msg += '\n'.join(cached_news)
    await update.callback_query.message.reply_text(msg, parse_mode='Markdown')

async def handle_buy_premium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "💳 *Premium Membership Benefits*\n\n"
        "✅ Exclusive premium stock picks.\n"
        "✅ Low-risk, high-confidence recommendations.\n"
        "✅ Early access to daily picks.\n"
        "💰 Premium Price: 99/month\n\n"
        "📩 Contact @Intradaypicks_admin to buy premium."
    )
    await update.callback_query.message.reply_text(msg, parse_mode='Markdown')

async def handle_my_user_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await update.callback_query.message.reply_text(f'Your Telegram User ID: `{user_id}`', parse_mode='Markdown')

async def add_premium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text("❌ You are not authorized.")
        return
    if len(context.args) != 1:
        await update.message.reply_text("Usage: /addpremium <user_id>")
        return
    user_id = int(context.args[0])
    premium_users.add(user_id)
    await update.message.reply_text(f"✅ User {user_id} added as premium.")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == 'intraday':
        await handle_intraday(update, context)
    elif query.data == 'news':
        await handle_news(update, context)
    elif query.data == 'buy_premium':
        await handle_buy_premium(update, context)
    elif query.data == 'my_user_id':
        await handle_my_user_id(update, context)

if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('addpremium', add_premium))
    app.add_handler(CallbackQueryHandler(button_handler))

    scheduler = AsyncIOScheduler()
    scheduler.add_job(refresh_data, 'cron', hour='9-16', minute='0')  # Refresh every hour between 9am to 4pm
    scheduler.start()

    print("Bot is running...")
    app.run_polling()