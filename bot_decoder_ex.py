"""
Decoder de tu Ex — Bot de Telegram
====================================
Bot para analizar mensajes de la ex con IA.

SETUP:
1. pip install python-telegram-bot anthropic
2. Crea un bot en @BotFather y obtén el TOKEN
3. Obtén tu ANTHROPIC_API_KEY en console.anthropic.com
4. Configura las variables de entorno:
   export TELEGRAM_TOKEN="tu_token_aqui"
   export ANTHROPIC_API_KEY="tu_key_aqui"
5. python bot.py

PAGOS (Producción):
- Usa Hotmart, Kiwifly o Stripe para cobrar la suscripción
- Guarda los user IDs activos en una base de datos (SQLite o PostgreSQL)
- Verifica el acceso en check_subscription() con tu lógica real
"""

import os
import logging
from anthropic import Anthropic
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "TU_TOKEN_AQUI")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "TU_KEY_AQUI")
PAYMENT_LINK = "https://tu-link-de-pago.com"  # Hotmart / Kiwify / Stripe

client = Anthropic(api_key=ANTHROPIC_API_KEY)

# ─────────────────────────────────────────
# SUSCRIPCIONES (simplificado — en producción usa DB)
# ─────────────────────────────────────────
ACTIVE_SUBSCRIBERS = set()  # En producción: consulta tu DB aquí
FREE_TRIAL_USES = {}         # user_id -> int (usos del período de prueba)
FREE_TRIAL_LIMIT = 2         # Análisis gratuitos antes de pedir pago


def check_subscription(user_id: int) -> bool:
    """Verifica si el usuario tiene suscripción activa."""
    return user_id in ACTIVE_SUBSCRIBERS


def get_free_uses(user_id: int) -> int:
    return FREE_TRIAL_USES.get(user_id, 0)


def increment_free_uses(user_id: int):
    FREE_TRIAL_USES[user_id] = get_free_uses(user_id) + 1


# ─────────────────────────────────────────
# PROMPT DEL SISTEMA
# ─────────────────────────────────────────
SYSTEM_PROMPT = """Eres el "Decoder de tu Ex", una IA especializada en análisis de comunicación emocional femenina y psicología del apego en el contexto de reconquista amorosa.

Tu misión es analizar mensajes que los usuarios reciben de su ex y ayudarlos a entender qué hay detrás de las palabras.

Cuando el usuario comparte un mensaje, debes responder SIEMPRE en este formato exacto:

🔍 *ANÁLISIS EMOCIONAL*
[Explica en 2-3 oraciones qué emoción o estado mental hay detrás del mensaje. Sé específico y directo.]

📊 *SEÑALES DETECTADAS*
• [Señal 1 con explicación breve]
• [Señal 2 con explicación breve]
• [Señal 3 si aplica]

💡 *LO QUE REALMENTE SIGNIFICA*
[1-2 oraciones directas sobre la intención real detrás del mensaje]

✉️ *RESPUESTA RECOMENDADA*
_"[La respuesta exacta que debe enviar, lista para copiar]"_

⚡ *Por qué esta respuesta funciona*
[Explica en 1-2 oraciones la estrategia detrás]

---
Reglas importantes:
- Sé siempre directo y práctico, no filosófico
- La respuesta recomendada debe ser corta, natural y estratégica
- Nunca des respuestas genéricas — analiza el mensaje específico
- Si el contexto es ambiguo, pide más información antes de analizar
- Usa lenguaje masculino latinoamericano casual pero inteligente
- Responde siempre en español"""


# ─────────────────────────────────────────
# HANDLERS
# ─────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    keyboard = [
        [InlineKeyboardButton("🔓 Activar acceso completo", url=PAYMENT_LINK)],
        [InlineKeyboardButton("🎯 Probar gratis (2 análisis)", callback_data="try_free")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"👋 Hola, *{user.first_name}*\n\n"
        "🔮 *Decoder de tu Ex* — IA que descifra sus mensajes\n\n"
        "Pega cualquier mensaje que te envió tu ex y te digo:\n"
        "• Qué emoción hay detrás de sus palabras\n"
        "• Qué señales ocultas detecta la IA\n"
        "• Exactamente qué responderle\n\n"
        "Tienes *2 análisis gratuitos* para probar 👇",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )


async def try_free_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "✅ *Modo prueba activado*\n\n"
        "Envíame el mensaje de tu ex ahora mismo.\n\n"
        "_Ejemplo: \"Ok, como quieras. No importa.\"_\n\n"
        "Solo pega el texto y la IA lo analiza al instante 👇",
        parse_mode="Markdown"
    )


async def analyze_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    message_text = update.message.text

    # Verificar acceso
    has_sub = check_subscription(user_id)
    free_uses = get_free_uses(user_id)

    if not has_sub and free_uses >= FREE_TRIAL_LIMIT:
        keyboard = [[InlineKeyboardButton(
            "🔓 Activar suscripción — $17/mes", url=PAYMENT_LINK
        )]]
        await update.message.reply_text(
            "⚠️ *Agotaste tus análisis gratuitos*\n\n"
            "Para continuar decifrando sus mensajes, activa tu suscripción:\n\n"
            "✅ Análisis ilimitados\n"
            "✅ Respuestas listas para copiar\n"
            "✅ Disponible 24/7\n"
            "✅ Cancela cuando quieras\n\n"
            "*Solo $17 USD/mes* 👇",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # Indicador de escritura
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action="typing"
    )

    # Llamada a la API de Anthropic
    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": f"Mi ex me escribió esto:\n\n\"{message_text}\"\n\n¿Qué significa y qué le respondo?"
                }
            ]
        )

        analysis = response.content[0].text

        # Registrar uso si es período de prueba
        if not has_sub:
            increment_free_uses(user_id)
            remaining = FREE_TRIAL_LIMIT - get_free_uses(user_id)
            footer = f"\n\n—\n_Análisis gratuitos restantes: {remaining}_"
            if remaining == 0:
                footer += "\n_¡Activa la suscripción para análisis ilimitados!_"
            analysis += footer

        await update.message.reply_text(analysis, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Error en análisis: {e}")
        await update.message.reply_text(
            "⚠️ Hubo un error al analizar el mensaje. Intenta nuevamente en unos segundos."
        )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 *Cómo usar el Decoder*\n\n"
        "1️⃣ Simplemente *pega el mensaje* que te envió tu ex\n"
        "2️⃣ La IA analiza el tono emocional y las señales ocultas\n"
        "3️⃣ Recibes la *respuesta exacta* para enviarle\n\n"
        "*Comandos:*\n"
        "/start — Menú principal\n"
        "/suscripcion — Ver estado de tu suscripción\n"
        "/cancelar — Cancelar suscripción\n"
        "/ayuda — Esta pantalla\n\n"
        "💡 *Tip:* Puedes pegar conversaciones completas, no solo un mensaje.",
        parse_mode="Markdown"
    )


async def subscription_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if check_subscription(user_id):
        await update.message.reply_text(
            "✅ *Suscripción activa*\n\n"
            "Tienes acceso ilimitado al Decoder.\n\n"
            "Para cancelar, usa /cancelar",
            parse_mode="Markdown"
        )
    else:
        free_uses = get_free_uses(user_id)
        remaining = max(0, FREE_TRIAL_LIMIT - free_uses)
        keyboard = [[InlineKeyboardButton("🔓 Activar suscripción", url=PAYMENT_LINK)]]
        await update.message.reply_text(
            f"📊 *Tu estado actual*\n\n"
            f"Suscripción: ❌ No activa\n"
            f"Análisis gratuitos restantes: *{remaining}*\n\n"
            "Activa tu suscripción para análisis ilimitados 👇",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


async def cancel_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    # En producción: cancela en tu plataforma de pagos aquí
    ACTIVE_SUBSCRIBERS.discard(user_id)
    await update.message.reply_text(
        "✅ Tu suscripción ha sido cancelada.\n\n"
        "Lamentamos verte partir. Si cambias de mente, "
        "puedes reactivarla en cualquier momento con /start",
        parse_mode="Markdown"
    )


# ─────────────────────────────────────────
# WEBHOOK PARA PAGOS (ejemplo con Hotmart)
# ─────────────────────────────────────────
"""
Para activar suscripciones automáticamente:

1. En Hotmart/Kiwify, configura un webhook POST a tu servidor
2. Cuando llegue un pago aprobado, extrae el telegram_user_id 
   (puedes pedirlo en el formulario de compra como campo personalizado)
3. Agrega el user_id a ACTIVE_SUBSCRIBERS (o tu DB)

Ejemplo con Flask:

from flask import Flask, request
app = Flask(__name__)

@app.route('/webhook/hotmart', methods=['POST'])
def hotmart_webhook():
    data = request.json
    if data.get('event') == 'PURCHASE_APPROVED':
        telegram_id = int(data['buyer']['extra_field_telegram_id'])
        ACTIVE_SUBSCRIBERS.add(telegram_id)
        # Guardar en DB
    return 'ok', 200
"""


# ─────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────
def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ayuda", help_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("suscripcion", subscription_status))
    app.add_handler(CommandHandler("cancelar", cancel_subscription))
    app.add_handler(CallbackQueryHandler(try_free_callback, pattern="^try_free$"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, analyze_message))

    logger.info("🔮 Decoder de tu Ex bot iniciado...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
