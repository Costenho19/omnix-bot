#!/usr/bin/env python3
"""
OMNIX Bot Universal - Sistema Funcional para Deployment FIXED
Bot Telegram completo con IA híbrida y trading crypto - Gemini API actualizada
"""

import os
import sqlite3
import asyncio
import logging
from datetime import datetime
import requests
import yfinance as yf

# Telegram imports
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

# Flask for health check
from flask import Flask, jsonify

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '8066618704:AAFaRX2uPRxQk17PHa8LwOLIIyM3DhlOJjg')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')

def init_database():
    """Initialize database"""
    try:
        conn = sqlite3.connect('omnix_bot.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                username TEXT,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS portfolio (
                user_id TEXT PRIMARY KEY,
                balance_usd REAL DEFAULT 10000.0,
                bitcoin REAL DEFAULT 0.0,
                ethereum REAL DEFAULT 0.0,
                solana REAL DEFAULT 0.0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Database initialized")
    except Exception as e:
        logger.error(f"Database error: {e}")

class OmnixBot:
    def __init__(self):
        self.responses = {
            'bitcoin': "Bitcoin está mostrando señales alcistas. Precio actual alrededor de $107K. Es una buena opción para HODLing a largo plazo.",
            'ethereum': "Ethereum mantiene fundamentos sólidos con su ecosistema DeFi. Precio cerca de $2.5K. Excelente para diversificación.",
            'solana': "Solana ha demostrado gran crecimiento. Precio aproximado $154. Tecnología rápida y escalable.",
            'trading': "Para trading exitoso: 1) Gestión de riesgo, 2) Análisis técnico, 3) Solo invierte lo que puedas perder.",
            'portfolio': "Tu portfolio virtual de $10,000 está listo para practicar trading sin riesgo real."
        }

    async def get_crypto_price(self, symbol):
        """Get real crypto price"""
        try:
            crypto_map = {
                'bitcoin': 'BTC-USD',
                'ethereum': 'ETH-USD', 
                'solana': 'SOL-USD',
                'btc': 'BTC-USD',
                'eth': 'ETH-USD',
                'sol': 'SOL-USD'
            }
            
            yahoo_symbol = crypto_map.get(symbol.lower(), f'{symbol.upper()}-USD')
            ticker = yf.Ticker(yahoo_symbol)
            data = ticker.history(period="1d")
            
            if not data.empty:
                return float(data['Close'].iloc[-1])
            return None
        except:
            return None

    def get_portfolio(self, user_id):
        """Get user portfolio"""
        try:
            conn = sqlite3.connect('omnix_bot.db')
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM portfolio WHERE user_id = ?', (user_id,))
            portfolio = cursor.fetchone()
            
            if not portfolio:
                cursor.execute('''
                    INSERT INTO portfolio (user_id) VALUES (?)
                ''', (user_id,))
                conn.commit()
                conn.close()
                return {'balance_usd': 10000.0, 'bitcoin': 0.0, 'ethereum': 0.0, 'solana': 0.0}
            
            conn.close()
            return {
                'balance_usd': portfolio[1],
                'bitcoin': portfolio[2], 
                'ethereum': portfolio[3],
                'solana': portfolio[4]
            }
        except:
            return {'balance_usd': 10000.0, 'bitcoin': 0.0, 'ethereum': 0.0, 'solana': 0.0}

    async def ask_gemini(self, question, user_id, username):
        """Ask Gemini AI with updated API"""
        try:
            if not GEMINI_API_KEY:
                return self.get_smart_response(question, username)
            
            # Updated API endpoint with correct model
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
            
            payload = {
                "contents": [{
                    "parts": [{
                        "text": f"Eres OMNIX, un experto en criptomonedas y trading. Responde en español de forma natural y profesional. Máximo 200 palabras. Pregunta: {question}"
                    }]
                }]
            }
            
            response = requests.post(url, json=payload, timeout=8)
            
            if response.status_code == 200:
                data = response.json()
                if 'candidates' in data and data['candidates']:
                    answer = data['candidates'][0]['content']['parts'][0]['text']
                    self.save_conversation(user_id, username, question, answer)
                    return answer
            
            return self.get_smart_response(question, username)
            
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            return self.get_smart_response(question, username)

    def get_smart_response(self, question, username):
        """Smart offline response"""
        question_lower = question.lower()
        
        # Detect crypto mentions
        if any(word in question_lower for word in ['bitcoin', 'btc']):
            return f"Hola {username}, {self.responses['bitcoin']}"
        elif any(word in question_lower for word in ['ethereum', 'eth']):
            return f"Hola {username}, {self.responses['ethereum']}"
        elif any(word in question_lower for word in ['solana', 'sol']):
            return f"Hola {username}, {self.responses['solana']}"
        elif any(word in question_lower for word in ['trading', 'trade', 'comprar', 'vender']):
            return f"Hola {username}, {self.responses['trading']}"
        elif any(word in question_lower for word in ['portfolio', 'cartera', 'balance']):
            return f"Hola {username}, {self.responses['portfolio']}"
        else:
            return f"Hola {username}, soy OMNIX, tu experto en criptomonedas. Puedo ayudarte con Bitcoin, Ethereum, Solana y estrategias de trading. ¿En qué crypto estás interesado?"

    def save_conversation(self, user_id, username, question, answer):
        """Save conversation"""
        try:
            conn = sqlite3.connect('omnix_bot.db')
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO conversations (user_id, username, question, answer)
                VALUES (?, ?, ?, ?)
            ''', (user_id, username, question, answer))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Save error: {e}")

# Bot instance
bot = OmnixBot()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command"""
    welcome_text = """🚀 ¡Hola! Soy OMNIX Bot

Tu asistente experto en criptomonedas más avanzado del mundo.

🎯 Puedo ayudarte con:
• Análisis de Bitcoin, Ethereum, Solana
• Consejos de trading personalizados  
• Portfolio virtual de $10,000
• Estrategias de inversión

Escribe /menu para opciones o pregúntame sobre cualquier crypto."""

    await update.message.reply_text(welcome_text)

async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menu command"""
    keyboard = [
        [InlineKeyboardButton("📊 Portfolio", callback_data='portfolio')],
        [InlineKeyboardButton("₿ Bitcoin", callback_data='bitcoin')],
        [InlineKeyboardButton("⟠ Ethereum", callback_data='ethereum')],
        [InlineKeyboardButton("◎ Solana", callback_data='solana')],
        [InlineKeyboardButton("📈 Trading", callback_data='trading')]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('🎛️ Menú OMNIX:', reply_markup=reply_markup)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks"""
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    username = query.from_user.username or query.from_user.first_name or "Usuario"
    
    if query.data == 'portfolio':
        portfolio = bot.get_portfolio(user_id)
        text = f"""💼 Portfolio OMNIX:

💰 USD: ${portfolio['balance_usd']:,.2f}
₿ Bitcoin: {portfolio['bitcoin']:.6f} BTC
⟠ Ethereum: {portfolio['ethereum']:.6f} ETH  
◎ Solana: {portfolio['solana']:.6f} SOL

🎯 ¡Listo para trading!"""
        await query.edit_message_text(text)
        
    elif query.data in ['bitcoin', 'ethereum', 'solana']:
        crypto = query.data
        price = await bot.get_crypto_price(crypto)
        
        if price:
            text = f"📊 {crypto.capitalize()}: ${price:,.2f} USD\n\nAnálisis: Tendencia positiva, fundamentales sólidos. Buen momento para considerar posición."
        else:
            text = f"📊 {crypto.capitalize()}\n\nAnálisis: Crypto con fundamentos sólidos y potencial de crecimiento a largo plazo."
            
        await query.edit_message_text(text)
        
    elif query.data == 'trading':
        text = """📈 Consejos Trading OMNIX:

1. 🎯 Define tu estrategia
2. 🛡️ Usa stop-loss siempre  
3. 💰 Invierte solo lo que puedas perder
4. 📊 Analiza antes de comprar
5. ⏰ HODL en proyectos sólidos

¡El trading requiere paciencia y disciplina!"""
        await query.edit_message_text(text)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle messages"""
    user_id = str(update.message.from_user.id)
    username = update.message.from_user.username or update.message.from_user.first_name or "Usuario"
    question = update.message.text
    
    # Send thinking message
    thinking_msg = await update.message.reply_text("🧠 Analizando...")
    
    try:
        # Get response using updated Gemini API
        answer = await bot.ask_gemini(question, user_id, username)
        await thinking_msg.edit_text(answer)
        
    except Exception as e:
        logger.error(f"Message error: {e}")
        await thinking_msg.edit_text("Disculpa, error temporal. Intenta de nuevo.")

async def portfolio_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Portfolio command"""
    user_id = str(update.message.from_user.id)
    portfolio = bot.get_portfolio(user_id)
    
    text = f"""💼 Tu Portfolio OMNIX:

💰 Balance USD: ${portfolio['balance_usd']:,.2f}
₿ Bitcoin: {portfolio['bitcoin']:.6f} BTC
⟠ Ethereum: {portfolio['ethereum']:.6f} ETH
◎ Solana: {portfolio['solana']:.6f} SOL

🚀 ¡Portfolio listo para trading!"""
    
    await update.message.reply_text(text)

# Flask app for health check
app = Flask(__name__)

@app.route('/health')
def health():
    return jsonify({"status": "healthy", "service": "omnix-bot"})

@app.route('/')
def home():
    return jsonify({
        "service": "OMNIX Bot",
        "status": "running",
        "message": "Bot funcionando globalmente 24/7"
    })

def main():
    """Main function"""
    # Initialize database
    init_database()
    
    # Create application
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("menu", menu_command))
    application.add_handler(CommandHandler("portfolio", portfolio_command))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Start bot
    logger.info("Starting OMNIX Bot...")
    application.run_polling()

if __name__ == "__main__":
    # For Render deployment
    port = int(os.environ.get("PORT", 5000))
    
    # Start Flask in background thread
    import threading
    flask_thread = threading.Thread(target=lambda: app.run(host='0.0.0.0', port=port))
    flask_thread.daemon = True
    flask_thread.start()
    
    # Start Telegram bot
    main()
